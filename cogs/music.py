import discord
from discord.ext import commands
from discord import app_commands, ui
import yt_dlp as ytdl
import asyncio
import subprocess
import random

ORANGE_COLOR = 0xFFA500  # Orange color for embeds

# --- Helper to check if ffmpeg is installed ---
def is_ffmpeg_installed():
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def get_youtube_audio(query):
    ytdl_opts = {
        "format": "bestaudio[abr<=320]/bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": True,
        "default_search": "ytsearch",
        "quiet": True,
        "extract_flat": False,
        "forceurl": True,
        "skip_download": True,
        "source_address": "0.0.0.0",
        "prefer_ffmpeg": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["web"],
                "player_skip": ["configs", "webpage"],
                "skip": ["dash", "hls"]
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    }
    with ytdl.YoutubeDL(ytdl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            info = info["entries"][0]
        return {
            "url": info["url"],
            "title": info.get("title", "Unknown Title"),
            "webpage_url": info.get("webpage_url", query)
        }

class MusicPlayer:
    def __init__(self, bot, guild):
        self.bot = bot
        self.guild = guild
        self.queue = asyncio.Queue()
        self.now_playing = None
        self.voice_client = None
        self.player_task = None
        self.play_next_song = asyncio.Event()

    async def player_loop(self, ctx):
        while True:
            self.play_next_song.clear()
            track = await self.queue.get()
            self.now_playing = track
            try:
                # Simplified FFmpeg options for maximum compatibility
                ffmpeg_options = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                }
                source = discord.FFmpegPCMAudio(
                    track["url"],
                    executable="ffmpeg",
                    **ffmpeg_options
                )
            except Exception as e:
                if 'ffmpeg' in str(e).lower():
                    await ctx.send(
                        "❌ **FFmpeg was not found!**\n"
                        "Please ensure FFmpeg is installed and available in your system PATH or environment.\n"
                        "See: https://ffmpeg.org/download.html"
                    )
                else:
                    await ctx.send(f"Error playing track: {e}")
                self.now_playing = None
                continue
            ctx.voice_client.play(
                source,
                after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next_song.set)
            )
            
            # Create embed for now playing with song name as title
            embed = discord.Embed(
                title=f"🎵 {track['title']}",
                description="**Now Playing**",
                color=ORANGE_COLOR,
                url=track['webpage_url']
            )
            embed.set_footer(text="Use the buttons below to control playback")
            
            # Create music control panel
            view = MusicControlPanel(self.bot)
            await ctx.send(embed=embed, view=view)
            
            await self.play_next_song.wait()
            self.now_playing = None

    def is_playing(self):
        return self.voice_client and self.voice_client.is_playing()

    def is_paused(self):
        return self.voice_client and self.voice_client.is_paused()

    def cleanup(self):
        try:
            self.voice_client.stop()
        except Exception:
            pass
        self.queue = asyncio.Queue()
        self.now_playing = None
        self.player_task = None

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.last_channels = {}  # Store last voice channels for auto-reconnect

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates for auto-reconnect"""
        if member.bot:
            return
            
        guild = member.guild
        voice_client = guild.voice_client
        
        # If bot is not connected, check if we should auto-reconnect
        if not voice_client and guild.id in self.last_channels:
            last_channel = self.last_channels[guild.id]
            # If user joins the last channel bot was in, auto-reconnect
            if after.channel and after.channel.id == last_channel:
                try:
                    await after.channel.connect()
                    # Auto-deafen the bot when auto-reconnecting
                    await guild.change_voice_state(channel=after.channel, self_deaf=True)
                    embed = discord.Embed(
                        title="🔄 Auto-Reconnected",
                        description=f"Rejoined {after.channel.name} automatically",
                        color=ORANGE_COLOR
                    )
                    # Try to send message to a text channel
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            await channel.send(embed=embed)
                            break
                except Exception:
                    pass
        
        # If bot gets disconnected, store the last channel
        elif voice_client and before.channel and not after.channel and member == guild.me:
            self.last_channels[guild.id] = before.channel.id

    def get_player(self, ctx):
        gid = ctx.guild.id
        if gid not in self.players:
            self.players[gid] = MusicPlayer(self.bot, ctx.guild)
        player = self.players[gid]
        player.voice_client = ctx.voice_client
        return player

    async def join_voice(self, ctx):
        if ctx.author.voice is None:
            embed = discord.Embed(
                title="❌ Error",
                description="You need to be in a voice channel to use this command.",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)
            return None
        channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            try:
                vc = await channel.connect()
                # Auto-deafen the bot when joining
                await ctx.guild.change_voice_state(channel=channel, self_deaf=True)
                # Store last channel for auto-reconnect
                self.last_channels[ctx.guild.id] = channel.id
            except Exception as e:
                await ctx.send(f"Failed to join: {e}")
                return None
        elif ctx.voice_client.channel != channel:
            try:
                vc = await ctx.voice_client.move_to(channel)
                # Auto-deafen the bot when moving
                await ctx.guild.change_voice_state(channel=channel, self_deaf=True)
                # Store last channel for auto-reconnect
                self.last_channels[ctx.guild.id] = channel.id
            except Exception as e:
                await ctx.send(f"Failed to move: {e}")
                return None
        else:
            vc = ctx.voice_client
            # Ensure bot is deafened even if already connected
            await ctx.guild.change_voice_state(channel=vc.channel, self_deaf=True)
        return vc

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query: str):
        """Play a song from YouTube by name or URL."""
        if not is_ffmpeg_installed():
            embed = discord.Embed(
                title="❌ FFmpeg Error",
                description="FFmpeg is not installed or not in PATH!\nPlease install FFmpeg and make sure it's accessible from your command line.",
                color=ORANGE_COLOR
            )
            embed.add_field(name="Help", value="See: https://ffmpeg.org/download.html", inline=False)
            await ctx.send(embed=embed)
            return

        vc = await self.join_voice(ctx)
        if not vc:
            return
        player = self.get_player(ctx)
        player.voice_client = vc
        try:
            info = get_youtube_audio(query)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Could not get audio: {e}",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)
            return
        await player.queue.put(info)
        
        embed = discord.Embed(
            title="✅ Added to Queue",
            description=f"**{info['title']}**",
            color=ORANGE_COLOR
        )
        embed.add_field(name="Position", value=f"{player.queue.qsize()}", inline=True)
        await ctx.send(embed=embed)

        if not player.player_task or player.player_task.done():
            player.player_task = self.bot.loop.create_task(player.player_loop(ctx))

    @app_commands.command(name="play", description="Play a song from YouTube by name or URL.")
    @app_commands.describe(query="Song name or YouTube URL")
    async def slash_play(self, interaction: discord.Interaction, query: str):
        if not is_ffmpeg_installed():
            await interaction.response.send_message(
                "❌ **FFmpeg is not installed or not in PATH!**\n"
                "Please install FFmpeg and make sure it's accessible from your command line.\n"
                "See: https://ffmpeg.org/download.html",
                ephemeral=True
            )
            return
        await interaction.response.defer()
        ctx = await self.bot.get_context(interaction)
        await self.play(ctx, query=query)

    @commands.command(name="pause")
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            embed = discord.Embed(
                title="⏸️ Paused",
                description="Music has been paused",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Nothing is playing.",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="pause", description="Pause the current song.")
    async def slash_pause(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.pause(ctx)

    @commands.command(name="resume")
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            embed = discord.Embed(
                title="▶️ Resumed",
                description="Music has been resumed",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Nothing is paused.",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="resume", description="Resume the current song.")
    async def slash_resume(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.resume(ctx)

    @commands.command(name="stop")
    async def stop(self, ctx):
        if ctx.voice_client:
            player = self.get_player(ctx)
            player.cleanup()
            await ctx.voice_client.disconnect()
            embed = discord.Embed(
                title="⏹️ Stopped",
                description="Music stopped and disconnected from voice channel",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Not connected to any voice channel.",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="stop", description="Stop playback and leave voice.")
    async def slash_stop(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.stop(ctx)

    @commands.command(name="skip")
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            embed = discord.Embed(
                title="⏭️ Skipped",
                description="Skipped to the next song",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Nothing is playing.",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="skip", description="Skip to the next song.")
    async def slash_skip(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.skip(ctx)

    @commands.command(name="queue")
    async def queue_(self, ctx):
        player = self.get_player(ctx)
        embed = discord.Embed(
            title="🎵 Music Queue",
            color=ORANGE_COLOR
        )
        
        if player.now_playing:
            embed.add_field(
                name="🎵 Now Playing",
                value=f"**{player.now_playing['title']}**",
                inline=False
            )
        else:
            embed.add_field(
                name="🎵 Now Playing",
                value="Nothing playing",
                inline=False
            )
            
        if player.queue.empty():
            embed.add_field(
                name="📋 Queue",
                value="Queue is empty",
                inline=False
            )
        else:
            items = list(player.queue._queue)
            queue_text = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(items[:10])])
            if len(items) > 10:
                queue_text += f"\n... and {len(items) - 10} more"
            embed.add_field(
                name="📋 Queue",
                value=queue_text,
                inline=False
            )
            
        await ctx.send(embed=embed)

    @app_commands.command(name="queue", description="Show the current song queue.")
    async def slash_queue(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.queue_(ctx)

    @commands.command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx):
        player = self.get_player(ctx)
        if player.now_playing:
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**{player.now_playing['title']}**",
                color=ORANGE_COLOR,
                url=player.now_playing['webpage_url']
            )
            embed.add_field(name="🔗 Link", value=f"[Click here]({player.now_playing['webpage_url']})", inline=True)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Nothing Playing",
                description="No music is currently playing.",
                color=ORANGE_COLOR
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="nowplaying", description="Show the currently playing song.")
    async def slash_nowplaying(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.nowplaying(ctx)

    @commands.command(name="247")
    async def two_four_seven(self, ctx):
        """Make bot stay in voice channel for 24/7 presence"""
        vc = await self.join_voice(ctx)
        if vc:
            # Store the channel for persistence
            self.last_channels[ctx.guild.id] = vc.channel.id
            embed = discord.Embed(
                title="🔒 24/7 Mode Enabled",
                description=f"Bot will stay in **{vc.channel.name}** and auto-reconnect when users join",
                color=ORANGE_COLOR
            )
            embed.add_field(
                name="Auto-Reconnect", 
                value="✅ Enabled - Bot will rejoin when users enter this channel",
                inline=False
            )
            await ctx.send(embed=embed)

    @app_commands.command(name="247", description="Make bot stay in voice channel for 24/7 presence")
    async def slash_two_four_seven(self, interaction: discord.Interaction):
        ctx = await self.bot.get_context(interaction)
        await self.two_four_seven(ctx)

    @commands.command(name="panel")
    async def panel(self, ctx):
        embed = discord.Embed(
            title="🎵 Music Control Panel",
            description="Use the buttons below to control music playback",
            color=ORANGE_COLOR
        )
        view = MusicPanel(self)
        await ctx.send(embed=embed, view=view)

class MusicPanel(ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @ui.button(label="Play/Pause", style=discord.ButtonStyle.primary)
    async def play_pause(self, interaction: discord.Interaction, button: ui.Button):
        ctx = await self.cog.bot.get_context(interaction)
        vc = ctx.voice_client
        if vc:
            if vc.is_playing():
                vc.pause()
                embed = discord.Embed(title="⏸️ Paused", description="Music has been paused", color=ORANGE_COLOR)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            elif vc.is_paused():
                vc.resume()
                embed = discord.Embed(title="▶️ Resumed", description="Music has been resumed", color=ORANGE_COLOR)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(title="❌ Error", description="Nothing is playing.", color=ORANGE_COLOR)
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title="❌ Error", description="Not connected.", color=ORANGE_COLOR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: ui.Button):
        ctx = await self.cog.bot.get_context(interaction)
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            embed = discord.Embed(title="⏭️ Skipped", description="Skipped to the next song", color=ORANGE_COLOR)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title="❌ Error", description="Nothing is playing.", color=ORANGE_COLOR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        ctx = await self.cog.bot.get_context(interaction)
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
            embed = discord.Embed(title="⏹️ Stopped", description="Music stopped and disconnected", color=ORANGE_COLOR)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            player = self.cog.get_player(ctx)
            player.cleanup()
        else:
            embed = discord.Embed(title="❌ Error", description="Not connected.", color=ORANGE_COLOR)
            await interaction.response.send_message(embed=embed, ephemeral=True)

class MusicControlPanel(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot

    @ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: ui.Button):
        # Respond immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        if guild and guild.voice_client and guild.voice_client.is_playing():
            guild.voice_client.stop()
            embed = discord.Embed(title="⏭️ Skipped", description="Skipped to the next song", color=ORANGE_COLOR)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title="❌ Error", description="Nothing is playing.", color=ORANGE_COLOR)
            await interaction.followup.send(embed=embed, ephemeral=True)

    @ui.button(label="⏸️ Pause", style=discord.ButtonStyle.primary)
    async def pause(self, interaction: discord.Interaction, button: ui.Button):
        # Respond immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        if guild and guild.voice_client and guild.voice_client.is_playing():
            guild.voice_client.pause()
            embed = discord.Embed(title="⏸️ Paused", description="Music has been paused", color=ORANGE_COLOR)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title="❌ Error", description="Nothing is playing.", color=ORANGE_COLOR)
            await interaction.followup.send(embed=embed, ephemeral=True)

    @ui.button(label="▶️ Resume", style=discord.ButtonStyle.success)
    async def resume(self, interaction: discord.Interaction, button: ui.Button):
        # Respond immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        if guild and guild.voice_client and guild.voice_client.is_paused():
            guild.voice_client.resume()
            embed = discord.Embed(title="▶️ Resumed", description="Music has been resumed", color=ORANGE_COLOR)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(title="❌ Error", description="Nothing is paused.", color=ORANGE_COLOR)
            await interaction.followup.send(embed=embed, ephemeral=True)

    @ui.button(label="📋 Queue", style=discord.ButtonStyle.secondary)
    async def show_queue(self, interaction: discord.Interaction, button: ui.Button):
        # Respond immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)
        
        cog = self.bot.get_cog('MusicCog')
        if cog:
            # Create a simple context object
            class SimpleContext:
                def __init__(self, guild, voice_client):
                    self.guild = guild
                    self.voice_client = voice_client
            
            ctx = SimpleContext(interaction.guild, interaction.guild.voice_client)
            player = cog.get_player(ctx)
            embed = discord.Embed(title="🎵 Music Queue", color=ORANGE_COLOR)
            
            if player.now_playing:
                embed.add_field(
                    name="🎵 Now Playing",
                    value=f"**{player.now_playing['title']}**",
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎵 Now Playing",
                    value="Nothing playing",
                    inline=False
                )
                
            if player.queue.empty():
                embed.add_field(
                    name="📋 Queue",
                    value="Queue is empty",
                    inline=False
                )
            else:
                items = list(player.queue._queue)
                queue_text = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(items[:5])])
                if len(items) > 5:
                    queue_text += f"\n... and {len(items) - 5} more"
                embed.add_field(
                    name="📋 Queue",
                    value=queue_text,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)

    @ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        # Respond immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        if guild and guild.voice_client:
            guild.voice_client.stop()
            await guild.voice_client.disconnect()
            embed = discord.Embed(title="⏹️ Stopped", description="Music stopped and disconnected", color=ORANGE_COLOR)
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            cog = self.bot.get_cog('MusicCog')
            if cog:
                # Create a simple context object
                class SimpleContext:
                    def __init__(self, guild, voice_client):
                        self.guild = guild
                        self.voice_client = voice_client
                
                ctx = SimpleContext(guild, None)
                player = cog.get_player(ctx)
                player.cleanup()
        else:
            embed = discord.Embed(title="❌ Error", description="Not connected.", color=ORANGE_COLOR)
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MusicCog(bot))