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
        guild_data[guild.id] ={
            "log_channel_id": None,
            "persistent_messages": False,
            "premium_level": 0,
        }
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
        msg_data = {
            "message_id": message.id,
            "channel_id": message.channel.id,
            "guild_id": message.guild.id,
            "author_id": message.author.id,
            "action": "create",
            "timestamp": datetime.datetime.now(tz=datetime.UTC),
        }
        if message.content:
            msg_data["content"] = message.content
        #if message.embeds:
        #    msg_data["embeds"] = [embed.to_dict() for embed in message.embeds]
        await db.simple_insert("messages", **msg_data)


@client.event
async def on_raw_message_edit(payload):
    if guild_data[payload.guild_id]["persistent_messages"]:
        msg_data = {
            "message_id": payload.message_id,
            "channel_id": payload.channel_id,
            "guild_id": payload.guild_id,
            "author_id": int(payload.data["author"]["id"]),
            "action": "edit",
            "timestamp": datetime.datetime.now(tz=datetime.UTC),
        }
        if payload.data["content"]:
            msg_data["content"] = payload.data["content"]
        #if payload.data["embeds"]:
        #    msg_data["embeds"] = payload.data["embeds"]
        await db.simple_insert("messages", **msg_data)

    if guild_data[payload.guild_id]["log_channel_id"]:
        log_channel = client.get_channel(guild_data[payload.guild_id]["log_channel_id"])
        if log_channel and isinstance(log_channel, discord.TextChannel):
            if payload.cached_message:
                embed = discord.Embed(
                    description=f"# Before\n{payload.cached_message.content}\n# After\n{payload.data['content']}",
                    color=MAIN_COLOR,
                    timestamp=datetime.datetime.now(tz=datetime.UTC)
                )
                embed.set_author(
                    name=payload.cached_message.author,
                    icon_url=payload.cached_message.author.display_avatar.url
                )
            else:
                if not guild_data[payload.guild_id]["persistent_messages"]:
                    return
                fetch_data = await db.fetch("SELECT author_id, content FROM messages WHERE message_id = $1 AND channel_id = $2 ORDER BY message_id DESC LIMIT 1", payload.message_id, payload.channel_id)
                if len(fetch_data) == 0:
                    return
                fetch_data = fetch_data[0]
                embed = discord.Embed(
                    description=f"# Before\n{fetch_data[1]}\n# After\n{payload.data['content']}",
                    color=MAIN_COLOR,
                    timestamp=datetime.datetime.now(tz=datetime.UTC)
                )
                embed.set_author(
                    name=payload.data["author"]["username"],
                    icon_url=f"https://cdn.discordapp.com/avatars/{payload.data['author']['id']}/{payload.data['author']['avatar_hash']}.{'gif' if payload.data['author']['avatar_hash'].startswith('a_') else 'png'}"
                )
            embed.set_footer(text="Message edited")
            await log_channel.send(embed=embed)
        else:
            guild_data[payload.guild_id]["log_channel_id"] = None
            await db.simple_update("guilds", f"guild_id = {payload.guild_id}", log_channel_id=None)


@client.event
async def on_raw_message_delete(payload):
    if guild_data[payload.guild_id]["persistent_messages"]:
        msg_data = {
            "message_id": payload.message_id,
            "channel_id": payload.channel_id,
            "guild_id": payload.guild_id,
            "action": "delete",
            "timestamp": datetime.datetime.now(tz=datetime.UTC),
        }
        if payload.cached_message:
            msg_data["author_id"] = payload.cached_message.author.id
            if payload.cached_message.content:
                msg_data["content"] = payload.cached_message.content
            #if payload.cached_message.embeds:
            #    msg_data["embeds"] = payload.cached_message.embeds
        else:
            fetch_data = await db.fetch("SELECT author_id, content FROM messages WHERE message_id = $1 AND channel_id = $2 ORDER BY message_id DESC LIMIT 1", payload.message_id, payload.channel_id)
            if len(fetch_data) == 0:
                    return
            fetch_data = fetch_data[0]
            msg_data["author_id"] = fetch_data[0]
            if fetch_data[1]:
                msg_data["content"] = fetch_data[1]
            #if fetch_data[2]:
            #    msg_data["embeds"] = fetch_data[2]
        await db.simple_insert("messages", **msg_data)

    if guild_data[payload.guild_id]["log_channel_id"]:
        log_channel = client.get_channel(guild_data[payload.guild_id]["log_channel_id"])
        if log_channel and isinstance(log_channel, discord.TextChannel):
            if payload.cached_message:
                embed = discord.Embed(
                    description=payload.cached_message.content,
                    color=MAIN_COLOR,
                    timestamp=datetime.datetime.now(tz=datetime.UTC)
                )
                embed.set_author(
                    name=payload.cached_message.author,
                    icon_url=payload.cached_message.author.display_avatar.url
                )
            else:
                if not guild_data[payload.guild_id]["persistent_messages"]:
                    return
                fetch_data = await db.fetch("SELECT author_id, content FROM messages WHERE message_id = $1 AND channel_id = $2 ORDER BY message_id DESC LIMIT 1", payload.message_id, payload.channel_id)
                if len(fetch_data) == 0:
                    return
                fetch_data = fetch_data[0]
                embed = discord.Embed(
                    description=fetch_data[1],
                    color=MAIN_COLOR,
                    timestamp=datetime.datetime.now(tz=datetime.UTC)
                )
                user = client.get_user(fetch_data[0])
                if not user:
                    user = await client.fetch_user(fetch_data[0])
                if isinstance(user, discord.User):
                    embed.set_author(
                        name=user.name,
                        icon_url=user.display_avatar.url # type: ignore
                    )
            embed.set_footer(text="Message deleted")
            await log_channel.send(embed=embed)
        else:
            guild_data[payload.guild_id]["log_channel_id"] = None
            await db.simple_update("guilds", f"guild_id = {payload.guild_id}", log_channel_id=None)


@client.tree.command(description="Set the channel where logs will be sent.")
@app_commands.checks.has_permissions(manage_guild=True)
async def logchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    await db.simple_update("guilds", f"guild_id = {interaction.guild.id}", log_channel_id=channel.id) # type: ignore
    guild_data[interaction.guild.id]["log_channel_id"] = channel.id # type: ignore
    await interaction.response.send_message(f"Log channel set to {channel.mention}", ephemeral=True)


@client.tree.command(description="Store new, edited, and deleted messages in the database. Improves logging effectiveness.")
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
