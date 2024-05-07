import discord
from typing import Optional, Literal
from discord import app_commands
from discord.ext import commands
from core.config import guild_data, MAIN_COLOR
from core.postgres import db
from core.locale import localize, localization

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    settings = app_commands.Group(
        name=localization["en-US"]["commands"]["settings_name"],
        description=localization["en-US"]["commands"]["settings_description"],
        guild_only=True,
        default_permissions=discord.Permissions(manage_guild=True),
    )


    @settings.command(
        name=localization["en-US"]["commands"]["settings_persistent_messages_name"],
        description=localization["en-US"]["commands"]["settings_persistent_messages_description"],
    )
    async def settings_persistent_messages(self, interaction: discord.Interaction, toggle: Literal["enable", "disable"]):
        option = {
            "enable": True,
            "disable": False,
        }

        await db.simple_update("guilds", f"guild_id = {interaction.guild_id}", persistent_messages=option[toggle])
        guild_data[interaction.guild_id]["persistent_messages"] = option[toggle]

        embed = discord.Embed(
            title=localize(interaction.guild_id, "settings", "persistent_messages_name"),
            description=localize(interaction.guild_id, "settings", "persistent_messages_enabled") if option[toggle] else localize(interaction.guild_id, "settings", "persistent_messages_disabled"),
            color=MAIN_COLOR,
        )
        if option[toggle]:
            embed.add_field(
                name=localize(interaction.guild_id, "settings", "persistent_messages_note_name"),
                value=localize(interaction.guild_id, "settings", "persistent_messages_note_description").format("https://discord.com/developers/docs/policies-and-agreements/developer-terms-of-service"),
                inline=False,
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @settings.command(
        name=localization["en-US"]["commands"]["settings_logchannel_name"],
        description=localization["en-US"]["commands"]["settings_logchannel_description"],
    )
    async def settings_logchannel(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel]):
        await db.simple_update("guilds", f"guild_id = {interaction.guild_id}", log_channel_id=channel.id if channel else None)
        guild_data[interaction.guild_id]["log_channel_id"] = channel.id if channel else None

        embed = discord.Embed(
            title=localize(interaction.guild_id, "settings", "logchannel_name"),
            description=localize(interaction.guild_id, "settings", "logchannel_enabled").format(channel.mention) if channel else localize(interaction.guild_id, "settings", "logchannel_disabled"),
            color=MAIN_COLOR,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Settings(bot))
