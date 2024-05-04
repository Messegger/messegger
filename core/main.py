import discord
import asyncio
from discord.ext import commands
from core.postgres import db
from core.config import config, MY_GUILD, localization, guild_data

def guild_data_defaults():
    return {
        "log_channel_id": None,
        "persistent_messages": False,
        "premium_level": 0,
        "locale": "en-US",
    }

message_delete_cache = set()

class Messegger(commands.AutoShardedBot):
    def __init__(self, config: dict):
        super().__init__(
            command_prefix='/',
            status=discord.Status.idle,
            activity=discord.Game("starting..."),
            max_messages=config["bot"]["max_message_cache"],
            shard_count=config["bot"]["shard_count"],
            shard_ids=config["bot"]["shard_ids"],
            intents=discord.Intents(
                members=True,
                guilds=True,
                guild_messages=True,
                message_content=True,
            )
        )
        self.config = config

    async def setup_hook(self):
        await self.tree.sync(guild=MY_GUILD)
        await self.tree.sync()

    async def _load_extensions(self):
        for cog in ["help", "settings", "snipe"]:
            await self.load_extension(f"core.cogs.{cog}")


async def _store_message(message: discord.Message, action: str):
    data = {
        "message_id": message.id,
        "channel_id": message.channel.id,
        "author_id": message.webhook_id or message.author.id,
        "action": action,
        "timestamp": message.edited_at or message.created_at,
        "is_webhook": False if message.webhook_id is None else True,
    }
    if message.content:
        data["content"] = message.content
    if len(message.attachments):
        attachments = []
        for attachment in message.attachments:
            attachments.append(f"{message.channel.id}/{attachment.id}/{attachment.filename}")
        data["attachments"] = attachments

    await db.simple_insert("messages", **data)

async def _log_message(old_message: discord.Message | None, message: discord.Message, log_channel: discord.TextChannel):
    embed = discord.Embed(
        description=message.content if not old_message else None,
        color=0xFFFF00 if old_message else 0xFF0000,
    )
    embed.set_author(
        name=message.author.name,
        icon_url=message.author.display_avatar,
    )
    if old_message:
        embed.add_field(
            name=localization["en-US"]["logging"]["message_before"],
            value=old_message.content,
            inline=False,
        )
        embed.add_field(
            name=localization["en-US"]["logging"]["message_after"],
            value=message.content,
            inline=False,
        )
    if message.attachments:
        attachments = []
        for attachment in message.attachments:
            attachments.append(f"[{attachment.filename}]({attachment.url})")
        embed.add_field(
            name=localization["en-US"]["logging"]["message_attachments"],
            value="\n".join(attachments),
            inline=False,
        )
    embed.set_footer(text=f"#{message.channel.name} ({message.channel.id})")

    await log_channel.send(embed=embed)


client = Messegger(config)


@client.event
async def on_shard_ready(shard_id):
    guild_ids = [guild.id for guild in client.guilds if guild.shard_id == shard_id]
    fetch_data = await db.fetch("SELECT * FROM guilds WHERE guild_id = ANY($1::bigint[])", guild_ids)
    for row in fetch_data:
        guild_data[row[0]] = {
            "log_channel_id": row[1],
            "persistent_messages": row[2],
            "premium_level": row[3],
        }
        guild_ids.remove(row[0])
    
    if len(guild_ids) > 0:
        for i in guild_ids:
            await db.simple_insert("guilds", guild_id=i, **guild_data_defaults())
            guild_data[i] = guild_data_defaults()

    await client.change_presence(status=discord.Status.online, shard_id=shard_id)


@client.event
async def on_guild_join(guild):
    try:
        await db.simple_insert("guilds", guild_id=guild.id, **guild_data_defaults())
        guild_data[guild.id] = guild_data_defaults()
    except:
        fetch_data = await db.fetch("SELECT log_channel_id, persistent_messages, premium_level FROM guilds WHERE guild_id = $1", guild.id)
        fetch_data = fetch_data[0]
        guild_data[guild.id] = {
            "log_channel_id": fetch_data[0],
            "persistent_messages": fetch_data[1],
            "premium_level": fetch_data[2],
        }


@client.event
async def on_guild_remove(guild):
    del guild_data[guild.id]


@client.event
async def on_message(message):
    if guild_data[message.guild.id]["persistent_messages"]:
        await _store_message(message, "create")


@client.event
async def on_message_edit(old_message, new_message):
    if guild_data[new_message.guild.id]["log_channel_id"] is not None:
        log_channel = new_message.guild.get_channel(guild_data[new_message.guild.id]["log_channel_id"])
        if log_channel:
            await _log_message(old_message, new_message, log_channel)
        else:
            guild_data[new_message.guild.id]["log_channel_id"] = None

    if guild_data[new_message.guild.id]["persistent_messages"]:
        await _store_message(new_message, "edit")


@client.event
async def on_message_delete(message):
    if guild_data[message.guild.id]["log_channel_id"] is not None:
        message_delete_cache.add((message.channel.id, message.id))
        log_channel = message.guild.get_channel(guild_data[message.guild.id]["log_channel_id"])
        if log_channel:
            await _log_message(None, message, log_channel)
        else:
            guild_data[message.guild.id]["log_channel_id"] = None

    if guild_data[message.guild.id]["persistent_messages"]:
        await _store_message(message, "delete")


@client.event
async def on_raw_message_edit(payload):
    if guild_data[payload.guild_id]["log_channel_id"] is not None:
        if not discord.utils.get(client.cached_messages, id=payload.message_id, channel__id=payload.channel_id):
            log_channel = client.get_channel(guild_data[payload.guild_id]["log_channel_id"])
            if not log_channel:
                guild_data[payload.guild_id]["log_channel_id"] = None
                await db.simple_update("guilds", f"guild_id = {payload.guild_id}", log_channel_id=None)
                return

            fetch_data = await db.fetch("SELECT author_id, content, attachments, is_webhook FROM messages WHERE message_id = $1 AND channel_id = $2 ORDER BY timestamp DESC LIMIT 1", payload.message_id, payload.channel_id)
            if len(fetch_data) == 0:
                return
            
            fetch_data = fetch_data[0]
            author = client.get_user(fetch_data[0])
            if not author:
                try:
                    author = await client.fetch_user(fetch_data[0])
                except:
                    pass
            
            embed = discord.Embed(color=0xFFFF00)
            if author:
                embed.set_author(
                    name=author.name,
                    icon_url=author.display_avatar,
                )
            else:
                embed.set_author(name=localization["en-US"]["logging"]["unknown_webhook"])
            if fetch_data[1]:
                embed.add_field(
                    name=localization["en-US"]["logging"]["message_before"],
                    value=fetch_data[1],
                    inline=False,
                )
                embed.add_field(
                    name=localization["en-US"]["logging"]["message_after"],
                    value=payload.data["content"],
                    inline=False,
                )
            if fetch_data[2]:
                attachment_urls = [f"[{i.split('/')[-1]}](https://cdn.discordapp.com/attachments/{i})" for i in fetch_data[2]]
                embed.add_field(
                    name=localization["en-US"]["logging"]["message_attachments"],
                    value="\n".join(attachment_urls),
                    inline=False,
                )
            channel = client.get_channel(payload.channel_id)
            embed.set_footer(text=f"#{channel.name} ({channel.id})")

            await log_channel.send(embed=embed)


@client.event
async def on_raw_message_delete(payload):
    await asyncio.sleep(0.1)
    if (payload.channel_id, payload.message_id) in message_delete_cache:
        message_delete_cache.remove((payload.channel_id, payload.message_id))
        return

    if guild_data[payload.guild_id]["log_channel_id"] is not None:
        if not discord.utils.get(client.cached_messages, id=payload.message_id, channel__id=payload.channel_id):
            log_channel = client.get_channel(guild_data[payload.guild_id]["log_channel_id"])
            if not log_channel:
                guild_data[payload.guild_id]["log_channel_id"] = None
                await db.simple_update("guilds", f"guild_id = {payload.guild_id}", log_channel_id=None)
                return
            
            fetch_data = await db.fetch("SELECT author_id, content, attachments, is_webhook FROM messages WHERE message_id = $1 AND channel_id = $2 ORDER BY timestamp DESC LIMIT 1", payload.message_id, payload.channel_id)
            if len(fetch_data) == 0:
                return
            
            fetch_data = fetch_data[0]
            author = client.get_user(fetch_data[0])
            if not author:
                try:
                    author = await client.fetch_user(fetch_data[0])
                except:
                    pass

            embed = discord.Embed(
                description=fetch_data[1],
                color=0xFF0000,
            )
            if author:
                embed.set_author(
                    name=author.name,
                    icon_url=author.display_avatar,
                )
            else:
                embed.set_author(name=localization["en-US"]["logging"]["unknown_webhook"])
            if fetch_data[2]:
                attachment_urls = [f"[{i.split('/')[-1]}](https://cdn.discordapp.com/attachments/{i})" for i in fetch_data[2]]
                embed.add_field(
                    name=localization["en-US"]["logging"]["message_attachments"],
                    value="\n".join(attachment_urls),
                )
            channel = client.get_channel(payload.channel_id)
            embed.set_footer(text=f"#{channel.name} ({channel.id})")

            await log_channel.send(embed=embed)
