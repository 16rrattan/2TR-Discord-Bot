import discord
from discord.ext import commands
import json
import os
import asyncio
from config.test_server_config import GUILD_ID  # Guild ID from config

DATA_FILE = "data/members.json"

class UserTracker(commands.Cog):
    """Track server member data (ID, role, join time)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Ensure data folder and file exist
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
            with open(DATA_FILE, "w") as f:
                json.dump({}, f)

        # Start syncing members as a background task
        self.bot.loop.create_task(self.sync_members())

    # -------------------------
    # JSON helpers
    # -------------------------
    def load_users(self) -> dict:
        with open(DATA_FILE, "r") as f:
            return json.load(f)

    def save_users(self, data: dict):
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    # -------------------------
    # Helper to get top role
    # -------------------------
    def get_roles(self, member: discord.Member):
        """Return a list of role names the member has (excluding @everyone)."""
        return [r.name for r in member.roles if r.name != "@everyone"]


    # -------------------------
    # Sync members from target guild
    # -------------------------
    async def sync_members(self):
        await self.bot.wait_until_ready()  # Wait until bot is fully connected

        # Wait for guild to appear in cache
        guild = self.bot.get_guild(GUILD_ID)
        while guild is None:
            print(f"Waiting for guild {GUILD_ID} to appear...")
            await asyncio.sleep(1)
            guild = self.bot.get_guild(GUILD_ID)

        print(f"Found guild: {guild.name}, syncing members...")

        data = self.load_users()

        async for member in guild.fetch_members(limit=None):
            data[str(member.id)] = {
                "name": member.name,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "role": self.get_roles
                (member),
            }

        self.save_users(data)
        print(f"UserTracker: synced {len(data)} members from guild {guild.name}")

    # -------------------------
    # Events
    # -------------------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != GUILD_ID:
            return  # Ignore other servers
        data = self.load_users()
        data[str(member.id)] = {
            "name": member.name,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "role": self.get_roles(member),
        }
        self.save_users(data)
        print(f"UserTracker: added {member.name}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.guild.id != GUILD_ID:
            return
        if before.roles == after.roles:
            return
        data = self.load_users()
        if str(after.id) in data:
            data[str(after.id)]["role"] = self.get_roles(after)
            self.save_users(data)
            print(f"UserTracker: updated role for {after.name}")

    # -------------------------
    # Commands
    # -------------------------
    @commands.command()
    async def userdata(self, ctx):
        """Show your stored member data."""
        data = self.load_users().get(str(ctx.author.id))
        if not data:
            return await ctx.send("No data found for you.")
        await ctx.send(f"**Member Data**\nID: {ctx.author.id}\nJoined: {data['joined_at']}\nRole: {data['role']}")

    @commands.command()
    async def allmembers(self, ctx):
        """Show all stored members (debug)."""
        data = self.load_users()
        if not data:
            return await ctx.send("No member data found.")
        msg = "\n".join(f"{info['name']} | {info['role']} | {info['joined_at']}" for info in data.values())
        await ctx.send(msg[:1990])  # truncate for Discord limit

# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(UserTracker(bot))
