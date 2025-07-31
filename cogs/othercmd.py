
import discord
from discord.ext import commands
from discord import app_commands
import asyncio

ORANGE_COLOR = 0xFFA500  # Orange color for embeds
OWNER_ID = 748814695825277002

class OtherCmdCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="owner", description="Show bot owner details")
    async def owner(self, interaction: discord.Interaction):
        """Show bot owner details"""
        try:
            owner = await self.bot.fetch_user(OWNER_ID)
            embed = discord.Embed(
                title="👑 Bot Owner",
                color=ORANGE_COLOR
            )
            embed.add_field(name="Name", value=owner.display_name, inline=True)
            embed.add_field(name="Username", value=f"@{owner.name}", inline=True)
            embed.add_field(name="Owner ID", value=str(OWNER_ID), inline=True)
            embed.set_thumbnail(url=owner.avatar.url if owner.avatar else owner.default_avatar.url)
            embed.set_footer(text=f"Bot created by {owner.display_name}")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Could not fetch owner details: {e}",
                color=ORANGE_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="say", description="Make the bot say something")
    @app_commands.describe(message="The message for the bot to say")
    async def say(self, interaction: discord.Interaction, message: str):
        """Make the bot say something (Owner only)"""
        if interaction.user.id != OWNER_ID:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="Only the bot owner can use this command.",
                color=ORANGE_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Delete the interaction response and send the message
        await interaction.response.send_message("✅ Message sent!", ephemeral=True)
        await interaction.followup.send(message)

    @app_commands.command(name="clear", description="Clear messages from the chat")
    @app_commands.describe(amount="Number of messages to delete (max 100)")
    async def clear(self, interaction: discord.Interaction, amount: int = 10):
        """Clear messages from the chat (Owner only)"""
        if interaction.user.id != OWNER_ID:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="Only the bot owner can use this command.",
                color=ORANGE_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if amount > 100:
            amount = 100
        elif amount < 1:
            amount = 1
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            deleted = await interaction.channel.purge(limit=amount)
            embed = discord.Embed(
                title="🗑️ Messages Cleared",
                description=f"Successfully deleted {len(deleted)} messages.",
                color=ORANGE_COLOR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to delete messages in this channel.",
                color=ORANGE_COLOR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {e}",
                color=ORANGE_COLOR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    # Regular prefix commands for owner
    @commands.command(name="owner")
    async def prefix_owner(self, ctx):
        """Show bot owner details (prefix command)"""
        try:
            owner = await self.bot.fetch_user(OWNER_ID)
            embed = discord.Embed(
                title="👑 Bot Owner",
                color=ORANGE_COLOR
            )
            embed.add_field(name="Name", value=owner.display_name, inline=True)
            embed.add_field(name="Username", value=f"@{owner.name}", inline=True)
            embed.add_field(name="Owner ID", value=str(OWNER_ID), inline=True)
            embed.set_thumbnail(url=owner.avatar.url if owner.avatar else owner.default_avatar.url)
            embed.set_footer(text=f"Bot created by {owner.display_name}")
            
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Could not fetch owner details: {e}",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)

    @commands.command(name="say")
    async def prefix_say(self, ctx, *, message: str):
        """Make the bot say something (Owner only)"""
        if ctx.author.id != OWNER_ID:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="Only the bot owner can use this command.",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)
            return
        
        await ctx.message.delete()
        await ctx.send(message)

    @commands.command(name="clear")
    async def prefix_clear(self, ctx, amount: int = 10):
        """Clear messages from the chat (Owner only)"""
        if ctx.author.id != OWNER_ID:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="Only the bot owner can use this command.",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)
            return
        
        if amount > 100:
            amount = 100
        elif amount < 1:
            amount = 1
        
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
            embed = discord.Embed(
                title="🗑️ Messages Cleared",
                description=f"Successfully deleted {len(deleted) - 1} messages.",
                color=ORANGE_COLOR
            )
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(3)
            await msg.delete()
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to delete messages in this channel.",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {e}",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(OtherCmdCog(bot))
