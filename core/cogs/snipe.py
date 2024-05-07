import discord
from typing import Optional
from discord import app_commands
from discord.ext import commands
from core.config import guild_data, MAIN_COLOR
from core.locale import localization, localize

snipes = dict()

class Snipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.author.bot:
            snipes[message.channel.id] = message

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        del snipes[channel.id]

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        for channel in guild.channels:
            del snipes[channel.id]

    @app_commands.command(
        name=localization["en-US"]["commands"]["snipe_name"],
        description=localization["en-US"]["commands"]["snipe_description"],
    )
    @app_commands.default_permissions(manage_messages=True)
    async def snipe(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel]):
        channel = channel or interaction.channel
        message = snipes.get(channel.id)
        if message:
            embed = discord.Embed(
                description=message.content,
                timestamp=message.edited_at or message.created_at,
                color=MAIN_COLOR,
            )
            embed.set_author(
                name=message.author.name,
                icon_url=message.author.display_avatar,
            )
            if len(message.attachments) > 0:
                attachment_urls = [f"[{attachment.filename}]({attachment.url})" for attachment in message.attachments]
                embed.add_field(
                    name=localize(interaction.guild_id, "logging", "message_attachments"),
                    value="\n".join(attachment_urls),
                    inline=False,
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(content=f":x: {localize(interaction.guild_id, "snipe", "no_message")}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Snipe(bot))
