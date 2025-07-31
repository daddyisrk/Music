import os

# FFmpeg is now installed via Nix in replit.nix

import discord
from discord.ext import commands
import asyncio

# Get Discord token from environment variables (Secrets)
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ Error: DISCORD_TOKEN not found in environment variables!")
    print("Please add your Discord bot token to Secrets with the key 'DISCORD_TOKEN'")
    exit(1)

# Get status configuration from environment variables
STATUS_TYPE = os.getenv("STATUS_TYPE", "playing").lower()  # playing, watching, listening, streaming
STATUS_MSG = os.getenv("STATUS_MSG", "🎵 Music | r!play")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True  # Required for music features

bot = commands.Bot(
    command_prefix="r!",
    intents=intents,
    help_command=None,  # Remove default help command
)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    
    # Set bot status
    try:
        if STATUS_TYPE == "playing":
            activity = discord.Game(name=STATUS_MSG)
        elif STATUS_TYPE == "watching":
            activity = discord.Activity(type=discord.ActivityType.watching, name=STATUS_MSG)
        elif STATUS_TYPE == "listening":
            activity = discord.Activity(type=discord.ActivityType.listening, name=STATUS_MSG)
        elif STATUS_TYPE == "streaming":
            activity = discord.Streaming(name=STATUS_MSG, url="https://twitch.tv/discord")
        else:
            activity = discord.Game(name=STATUS_MSG)  # Default to playing
        
        await bot.change_presence(activity=activity)
        print(f"Status set to: {STATUS_TYPE.title()} {STATUS_MSG}")
    except Exception as e:
        print(f"Error setting status: {e}")
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Error syncing commands: {e}")

async def main():
    # Load cogs
    await bot.load_extension("cogs.music")
    await bot.load_extension("cogs.othercmd")
    await bot.load_extension("cogs.help")
    # Start the bot
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())