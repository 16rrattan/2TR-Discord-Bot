import discord
from discord.ext import commands, tasks
from datetime import datetime
from config.test_server_config import GUILD_ID, ROLE_IDS

# Prerequisite for "New Member" role
PREREQUISITE_ROLE = "Member"

# Milestone roles: "Role name": days required on server
MILESTONES = {
   ROLE_IDS["3_months"]: 90,
   ROLE_IDS["6_months"]: 180,
   ROLE_IDS["1_year"]: 365,
   ROLE_IDS["2_year"]: 730,
   ROLE_IDS["3_year"]: 1095,
}

PATREON_ROLE = ROLE_IDS["patreon_role"]
NEW_MEMBER_ROLE = ROLE_IDS["new_member"]

class MilestoneRoles(commands.Cog):
    """Assigns roles based on time on server and prerequisite roles."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_roles.start()  # start background task

    # -------------------------
    # Background Task
    # -------------------------
    @tasks.loop(seconds=10)
    async def check_roles(self):
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            print(f"MilestoneRoles: guild {GUILD_ID} not found")
            return

        now = datetime.utcnow()
        for member in guild.members:
            if member.bot or not member.joined_at:
                continue
            await self.update_member_roles(member, now)

    async def update_member_roles(self, member: discord.Member, now: datetime):
        """Assign or remove roles based on server time and prerequisites."""
        days_on_server = (now - member.joined_at).days

        # Handle "New Member" role first
        prereq_role = discord.utils.get(member.guild.roles, name=PREREQUISITE_ROLE)
        new_member_role = discord.utils.get(member.guild.roles, name=NEW_MEMBER_ROLE)

        if prereq_role and prereq_role in member.roles and days_on_server < 90:
            if new_member_role and new_member_role not in member.roles:
                await member.add_roles(new_member_role)
                print(f"Added {NEW_MEMBER_ROLE} to {member.name}")
        else:
            # Remove "New Member" if they no longer qualify
            if new_member_role and new_member_role in member.roles:
                await member.remove_roles(new_member_role)
                print(f"Removed {NEW_MEMBER_ROLE} from {member.name}")

        # Handle milestone roles
        for role_name, required_days in MILESTONES.items():
            role = discord.utils.get(member.guild.roles, name=role_name)
            if not role:
                continue

            if days_on_server >= required_days and role not in member.roles:
                # Remove any older milestone roles
                for old_role_name in MILESTONES:
                    old_role = discord.utils.get(member.guild.roles, name=old_role_name)
                    if old_role in member.roles and old_role != role:
                        await member.remove_roles(old_role)
                # Remove "New Member" role when promoting
                if new_member_role and new_member_role in member.roles:
                    await member.remove_roles(new_member_role)
                # Assign new milestone role
                await member.add_roles(role)
                print(f"Added {role.name} to {member.name}")

    @check_roles.before_loop
    async def before_loop(self):
        print("MilestoneRoles: Waiting for bot to be ready...")

# -------------------------
# Cog setup
# -------------------------
async def setup(bot):
    await bot.add_cog(MilestoneRoles(bot))
