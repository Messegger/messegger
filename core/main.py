import discord
import datetime
from discord import app_commands
from typing import Literal
from core.postgres import db
from core.config import config

MY_GUILD = discord.Object(id=config["bot"]["main_guild_id"])
MAIN_COLOR = config["bot"]["main_color"]

guild_data = dict()

def guild_data_defaults():
    return {
        "log_channel_id": None,
        "persistent_messages": False,
        "premium_level": 0,
    }

class Messegger(discord.AutoShardedClient):
    def __init__(self, config: dict):
        super().__init__(
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
        self.tree = app_commands.CommandTree(self)
        self.config = config

    async def setup_hook(self):
        await self.tree.sync(guild=MY_GUILD)
        await self.tree.sync()


async def _store_message(msg_payload: discord.Message | discord.RawMessageUpdateEvent | discord.RawMessageDeleteEvent, action: str):
    msg_data = {
        "action": action,
        "timestamp": datetime.datetime.now(tz=datetime.UTC),
    }

    # TODO: find a better way to do this...

    if isinstance(msg_payload, discord.Message):
        msg_data["message_id"] = msg_payload.id
        msg_data["channel_id"] = msg_payload.channel.id
        msg_data["guild_id"] = msg_payload.guild.id # type: ignore
        msg_data["author_id"] = msg_payload.webhook_id or msg_payload.author.id
        msg_data["is_webhook"] = (True if msg_payload.webhook_id else False)
        if msg_payload.content:
            msg_data["content"] = msg_payload.content
        if len(msg_payload.attachments) > 0:
            msg_data["attachments"] = [f"{msg_payload.channel.id}/{attachment.id}/{attachment.filename}" for attachment in msg_payload.attachments]
    elif isinstance(msg_payload, (discord.RawMessageUpdateEvent, discord.RawMessageDeleteEvent)):
        msg_data["message_id"] = msg_payload.message_id
        msg_data["channel_id"] = msg_payload.channel_id
        msg_data["guild_id"] = msg_payload.guild_id
        if isinstance(msg_payload, discord.RawMessageUpdateEvent):
            if "author" in msg_payload.data:
                if "webhook_id" in msg_payload.data:
                    msg_data["author_id"] = int(msg_payload.data["webhook_id"])
                    msg_data["is_webhook"] = True
                else:
                    msg_data["author_id"] = int(msg_payload.data["author"]["id"])
                    msg_data["is_webhook"] = False
            if "content" in msg_payload.data:
                msg_data["content"] = msg_payload.data["content"]
            if len(msg_payload.data["attachments"]) > 0:
                msg_data["attachments"] = [f"{msg_payload.data['channel_id']}/{attachment['id']}/{attachment['filename']}" for attachment in msg_payload.data["attachments"]]
        elif isinstance(msg_payload, discord.RawMessageDeleteEvent):
            fetch_data = await db.fetch("SELECT author_id, content, attachments, embeds, is_webhook FROM messages WHERE message_id = $1 AND channel_id = $2 ORDER BY message_id DESC LIMIT 1", msg_payload.message_id, msg_payload.channel_id)
            if len(fetch_data) == 0:
                return
            fetch_data = fetch_data[0]
            msg_data["author_id"] = fetch_data[0]
            msg_data["content"] = fetch_data[1]
            if fetch_data[2]:
                msg_data["attachments"] = fetch_data[2]
            msg_data["is_webhook"] = fetch_data[4]

    await db.simple_insert("messages", **msg_data)

async def _log_message_fetch(msg_payload: discord.RawMessageUpdateEvent | discord.RawMessageDeleteEvent):
    return await db.fetch("SELECT author_id, content, attachments, is_webhook FROM messages WHERE message_id = $1 AND channel_id = $2 ORDER BY message_id DESC LIMIT 1", msg_payload.message_id, msg_payload.channel_id)

async def _log_message(msg_payload: discord.RawMessageUpdateEvent | discord.RawMessageDeleteEvent, log_channel_id: int):
    log_channel = client.get_channel(log_channel_id)
    if not log_channel:
        guild_data[msg_payload.guild_id]["log_channel_id"] = None
        await db.simple_update("guilds", f"guild_id = {msg_payload.guild_id}", log_channel_id=None)
        return

    timestamp = datetime.datetime.now(tz=datetime.UTC)
    fetch_data = None

    # TODO: find a better way to do this...

    if msg_payload.cached_message:
        msg_content = msg_payload.cached_message.content
        msg_author = msg_payload.cached_message.author
        msg_attachments = [f"[{attachment.filename}]({attachment.url})" for attachment in msg_payload.cached_message.attachments] if len(msg_payload.cached_message.attachments) > 0 else None
    elif guild_data[msg_payload.guild_id]["persistent_messages"]:
        if not fetch_data:
            fetch_data = await _log_message_fetch(msg_payload)
            if len(fetch_data) == 0:
                return
            fetch_data = fetch_data[0]
        msg_content = fetch_data[1]
        msg_author = client.get_user(fetch_data[0]) if not fetch_data[3] else "Webhook"
        msg_attachments = [f"[{url.split('/')[-1]}](https://cdn.discordapp.com/attachments/{url})" for url in fetch_data[2]] if fetch_data[2] else None
    else:
        return

    embed = discord.Embed(
        title="Message Edited" if isinstance(msg_payload, discord.RawMessageUpdateEvent) else "Message Deleted",
        description=msg_content if isinstance(msg_payload, discord.RawMessageDeleteEvent) else None,
        color=0xFFFF00 if isinstance(msg_payload, discord.RawMessageUpdateEvent) else 0xFF0000,
        timestamp=timestamp,
    )
    embed.set_author(
        name=str(msg_author),
        icon_url=msg_author.display_avatar.url, # type: ignore
    )
    if isinstance(msg_payload, discord.RawMessageUpdateEvent):
        embed.add_field(
            name="Before",
            value=msg_content,
            inline=False,
        )
        embed.add_field(
            name="After",
            value=msg_payload.data["content"],
            inline=False,
        )
    if msg_attachments:
        embed.add_field(
            name="Attachments",
            value="\n".join(msg_attachments),
            inline=False,
        )

    await log_channel.send(embed=embed) # type: ignore


client = Messegger(config)


@client.event
async def on_shard_ready(shard_id):
    guild_ids = [guild.id for guild in client.guilds if guild.shard_id == shard_id]
    fetch_data = await db.fetch("SELECT * FROM guilds WHERE guild_id = ANY($1::bigint[])", guild_ids)
    for guild in fetch_data:
        guild_data[guild[0]] = {
            "log_channel_id": guild[1],
            "persistent_messages": guild[2],
            "premium_level": guild[3],
        }
        guild_ids.remove(guild[0])

    if len(guild_ids) > 0:
        for guild_id in guild_ids:
            await db.simple_insert("guilds", guild_id=guild_id, **guild_data_defaults())
            guild_data[guild_id] = guild_data_defaults()

    await client.change_presence(status=discord.Status.online, shard_id=shard_id)


@client.event
async def on_guild_join(guild):
    try:
        await db.simple_insert("guilds", guild_id=guild.id, **guild_data_defaults())
        guild_data[guild.id] = guild_data_defaults()
    except:
        fetch_data = await db.fetch("SELECT * FROM guilds WHERE guild_id = $1", guild.id)
        fetch_data = fetch_data[0]
        guild_data[guild.id] = {
            "log_channel_id": fetch_data[1],
            "persistent_messages": fetch_data[2],
            "premium_level": fetch_data[3],
        }


@client.event
async def on_guild_remove(guild):
    del guild_data[guild.id]


@client.event
async def on_message(message):
    if guild_data[message.guild.id]["persistent_messages"]:
        try:
            await _store_message(message, "create")
        except:
            pass


@client.event
async def on_raw_message_edit(payload):
    if guild_data[payload.guild_id]["log_channel_id"]:
        try:
            await _log_message(payload, guild_data[payload.guild_id]["log_channel_id"])
        except:
            guild_data[payload.guild_id]["log_channel_id"] = None
            await db.simple_update("guilds", f"guild_id = {payload.guild_id}", log_channel_id=None)
    if guild_data[payload.guild_id]["persistent_messages"]:
        try:
            await _store_message(payload, "edit")
        except:
            pass


@client.event
async def on_raw_message_delete(payload):
    if guild_data[payload.guild_id]["log_channel_id"]:
        try:
            await _log_message(payload, guild_data[payload.guild_id]["log_channel_id"])
        except:
            guild_data[payload.guild_id]["log_channel_id"] = None
            await db.simple_update("guilds", f"guild_id = {payload.guild_id}", log_channel_id=None)
    if guild_data[payload.guild_id]["persistent_messages"]:
        try:
            await _store_message(payload, "delete")
        except:
            pass


@client.tree.command(description="Get help.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Messegger Help [WIP]",
        description="Discord bot that tries to provide the leading message logging and moderation features.",
        color=MAIN_COLOR,
    )
    embed.add_field(
        name="Links",
        value=f"Join the [support server](https://discord.gg/rWVHU3qjvK) for help and updates.\n\nMore information about the bot [here](https://github.com/Messegger/messegger).\n\n[Add me to your server](https://discord.com/oauth2/authorize?client_id={client.user.id}&permissions=0&scope=bot)", # type: ignore
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.tree.command(description="Set the channel where logs will be sent.")
@app_commands.checks.has_permissions(manage_guild=True)
async def logchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    await db.simple_update("guilds", f"guild_id = {interaction.guild.id}", log_channel_id=channel.id) # type: ignore
    guild_data[interaction.guild.id]["log_channel_id"] = channel.id # type: ignore
    await interaction.response.send_message(f"Log channel set to {channel.mention}", ephemeral=True)


@client.tree.command(description="Store a copy of new, edited, and deleted messages. Improves logging effectiveness.")
@app_commands.checks.has_permissions(manage_guild=True)
async def persistentmessages(interaction: discord.Interaction, state: Literal["enable", "disable"]):
    state_bool = {
        "enable": True,
        "disable": False,
    }
    await db.simple_update("guilds", f"guild_id = {interaction.guild.id}", persistent_messages=state_bool[state]) # type: ignore
    guild_data[interaction.guild.id]["persistent_messages"] = state_bool[state] # type: ignore
    embed = discord.Embed(
        title="Persistent Messages",
        description=f":ballot_box_with_check: Persistent messages have been {state}d.",
        color=MAIN_COLOR,
    )
    if state == "enable":
        embed.add_field(name="Important Note", value="Due to Discord's Developer Terms of Service, messages older than 30 days are subject to automatic deletion regardless of this setting.")
    await interaction.response.send_message(embed=embed, ephemeral=True)
