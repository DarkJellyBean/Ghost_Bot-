from dotenv import load_dotenv
import os
import discord
from discord.ext import commands
import aiohttp
import asyncio

# Load .env (token & webhook)
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
LUMI_WEBHOOK = os.getenv("LUMI_WEBHOOK")

# --- STARTUP EVENT ---
@bot.event
async def on_ready():
    print(f"👻 Ghost_Bot online as {bot.user}")
    await bot.change_presence(activity=discord.Game(name="Tending the LUMI Realm"))

# --- BASIC COMMANDS ---
@bot.command()
async def ping(ctx):
    await ctx.send("👻 Boo! Ghost_Bot is awake and listening across the LUMI network.")

@bot.command()
async def feed(ctx):
    await ctx.send("✨ You feed the Orb. Faint pulses of light ripple through the LUMI realm...")

@bot.command()
async def dream(ctx):
    await ctx.send("💤 You drift into the dream portal — whispers of creation surround you.")

# --- OPTIONAL: WEBHOOK TEST ---
async def lumi_post(event_type, data):
    if not LUMI_WEBHOOK:
        return
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(LUMI_WEBHOOK, json={"event": event_type, "data": data})
        except Exception as e:
            print(f"LUMI post failed: {e}")

bot.run(os.getenv("TOKEN"))
