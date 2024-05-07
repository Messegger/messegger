import discord
from typing import Optional, Literal
from discord import app_commands
from discord.ext import commands
from core.config import guild_data, MAIN_COLOR
from core.locale import localize, localization

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name=localization["en-US"]["commands"]["help_name"],
        description=localization["en-US"]["commands"]["help_description"],
    )
    async def help(self, interaction: discord.Interaction, command: Optional[Literal["help", "settings", "snipe"]]):
        if not command:
            embed = discord.Embed(
                title=localize(interaction.guild_id, "help", "title"),
                description=localize(interaction.guild_id, "help", "description"),
                color=MAIN_COLOR,
            )
            embed.add_field(
                name=localize(interaction.guild_id, "help", "links_name"),
                value=localize(interaction.guild_id, "help", "links_value").format(
                    f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=0&scope=bot",
                    "https://top.gg/bot/1226243129733156906",
                    "https://discord.gg/rWVHU3qjvK",
                ),
                inline=False,
            )
        else:
            embed = discord.Embed(
                title=f"`/{command}`",
                description=localize(interaction.guild_id, "help", f"command_{command}_description"),
                color=MAIN_COLOR,
            )
            embed.add_field(
                name=localize(interaction.guild_id, "help", "permissions_name"),
                value=localize(interaction.guild_id, "help", "permissions_value"),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))
