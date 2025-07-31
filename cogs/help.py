
import discord
from discord.ext import commands
from discord import app_commands, ui

ORANGE_COLOR = 0xFFA500  # Orange color for embeds

class HelpView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Create a link button properly
        self.add_item(discord.ui.Button(
            label="🛠️ Support Server",
            style=discord.ButtonStyle.link,
            url="https://discord.gg/bcjrk4Q3np"
        ))

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        """Show all available commands"""
        embed = discord.Embed(
            title="🎵 BeatMate - Command List",
            description="Here are all available commands for the music bot!",
            color=ORANGE_COLOR
        )
        
        # Music Commands
        embed.add_field(
            name="🎵 Music Commands",
            value=(
                "`r!play <song>` - Play a song from YouTube\n"
                "`r!pause` - Pause the current song\n"
                "`r!resume` - Resume the paused song\n"
                "`r!skip` - Skip to the next song\n"
                "`r!stop` - Stop music and disconnect\n"
                "`r!queue` - Show the current queue\n"
                "`r!nowplaying` - Show currently playing song\n"
                "`r!247` - Enable 24/7 mode in voice channel\n"
                "`r!panel` - Show music control panel"
            ),
            inline=False
        )
        
        # Owner Commands
        embed.add_field(
            name="👑 Other Commands",
            value=(
                "`r!owner` - Show bot owner details\n"
                "`r!say <message>` - Make bot say something\n"
                "`r!clear <amount>` - Clear messages (max 100)"
            ),
            inline=False
        )
        
        # Slash Commands
        embed.add_field(
            name="⚡ Slash Commands",
            value=(
                "All prefix commands also work as slash commands!\n"
                "Use `/play`, `/pause`, `/resume`, etc.\n"
                "Type `/` to see all available slash commands"
            ),
            inline=False
        )
        
        # Additional Info
        embed.add_field(
            name="ℹ️ Additional Info",
            value=(
                "• Prefix: `r!`\n"
                "• Bot supports YouTube URLs and search queries\n"
                "• Music control buttons appear when playing\n"
                "• 24/7 mode keeps bot in voice channel"
            ),
            inline=False
        )
        
        embed.set_footer(text="Need help? Join our support server!")
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        view = HelpView()
        await ctx.send(embed=embed, view=view)

    @app_commands.command(name="help", description="Show all available commands")
    async def slash_help(self, interaction: discord.Interaction):
        """Show all available commands (slash command)"""
        embed = discord.Embed(
            title="🎵 BeatMate - Command List",
            description="Here are all available commands for the music bot!",
            color=ORANGE_COLOR
        )
        
        # Music Commands
        embed.add_field(
            name="🎵 Music Commands",
            value=(
                "`/play <song>` - Play a song from YouTube\n"
                "`/pause` - Pause the current song\n"
                "`/resume` - Resume the paused song\n"
                "`/skip` - Skip to the next song\n"
                "`/stop` - Stop music and disconnect\n"
                "`/queue` - Show the current queue\n"
                "`/nowplaying` - Show currently playing song\n"
                "`/247` - Enable 24/7 mode in voice channel\n"
                "`r!panel` - Show music control panel"
            ),
            inline=False
        )
        
        # Owner Commands
        embed.add_field(
            name="👑 Owner Commands",
            value=(
                "`/owner` - Show bot owner details\n"
                "`/say <message>` - Make bot say something\n"
                "`/clear <amount>` - Clear messages (max 100)"
            ),
            inline=False
        )
        
        # Prefix Commands
        embed.add_field(
            name="🔤 Prefix Commands",
            value=(
                "All slash commands also work with prefix `r!`\n"
                "Use `r!play`, `r!pause`, `r!resume`, etc.\n"
                "Type `r!help` to see this menu again"
            ),
            inline=False
        )
        
        # Additional Info
        embed.add_field(
            name="ℹ️ Additional Info",
            value=(
                "• Prefix: `r!`\n"
                "• Bot supports YouTube URLs and search queries\n"
                "• Music control buttons appear when playing\n"
                "• 24/7 mode keeps bot in voice channel"
            ),
            inline=False
        )
        
        embed.set_footer(text="Need help? Join our support server!")
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        view = HelpView()
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
