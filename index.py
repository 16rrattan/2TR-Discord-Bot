import discord
from discord.ext import commands
from config.test_server_config import (
    TOKEN,
    PREFIX,
    DATA_FILE,
    GUILD_ID,
    ROLE_IDS,
    WELCOME_CHANNEL,
    ANNOUNCEMENT_CHANNEL,
    MILESTONE_CHANNELS,
)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# -------------------------
# Events
# -------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# -------------------------
# Load cogs
# -------------------------
async def load_cogs():
    await bot.load_extension("cogs.member_tracker")      # your member tracker
    await bot.load_extension("cogs.milestone_roles")     # NEW cog

# -------------------------
# Start bot
# -------------------------
async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())
