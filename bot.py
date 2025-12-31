import discord
from discord.ext import tasks, commands
import json
import os
from datetime import datetime
import io
from PIL import Image, ImageDraw, ImageFont
import aiohttp

#import config
from official_server_config import (
    TOKEN,
    DATA_FILE,
    PATREON_ROLE,
    MILESTONE_ROLES,
    WELCOME_CHANNEL,
    ANNOUNCEMENT_CHANNEL,
    MILESTONE_CHANNELS,
)

# Set up the bot with intents
intents = discord.Intents.default()
intents.members = True  # Enable member-related events
bot = commands.Bot(command_prefix='!', intents=intents)


# Load or initialize member data
member_data = {}
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        member_data = json.load(f)

# When the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await initialize_member_data()
    check_roles.start()  # Start the daily role check task

async def initialize_member_data():
    for guild in bot.guilds:
        async for member in guild.fetch_members(limit=None):
            if not member.bot:
                if str(member.id) not in member_data:
                    member_data[str(member.id)] = {
                        'join_date': member.joined_at.timestamp()
                    }
                elif member_data[str(member.id)]['join_date'] != member.joined_at.timestamp():
                    member_data[str(member.id)]['join_date'] = member.joined_at.timestamp()
    with open(DATA_FILE, 'w') as f:
        json.dump(member_data, f, indent=2)
    print('Member data initialized')

@bot.event
async def on_member_join(member):
    if not member.bot:
        member_data[member.id] = {
            'join_date': member.joined_at.timestamp()
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(member_data, f, indent=2)
        print(f'{member.name} joined on {member.joined_at}')



# Function to create a custom welcome image
async def create_background_image(member, line1="Welcome,", line2=None, role_name=None):
    # Load the background image (assuming 1200x400)
    background = Image.open("background.png").convert("RGBA")
    bg_width, bg_height = background.size  # Get background dimensions

    # Fetch the member's avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(member.display_avatar.url) as resp:
            if resp.status == 200:
                avatar_data = io.BytesIO(await resp.read())
                avatar = Image.open(avatar_data).convert("RGBA")
            else:
                avatar = Image.new("RGBA", (300, 300), (255, 255, 255, 255))
    
    # Increase avatar size (e.g., 300x300)
    avatar_size = 400
    avatar = avatar.resize((avatar_size, avatar_size), Image.LANCZOS)

    # Create a circular mask for the avatar
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
    avatar.putalpha(mask)

    # Center the avatar horizontally and adjust vertically to leave room for text below
    avatar_x = (bg_width - avatar_size) // 2  # Center horizontally
    avatar_y = (bg_height - avatar_size) // 2 - 150  # Shift up slightly to balance with text below
    background.paste(avatar, (avatar_x, avatar_y), avatar)

    # Add welcome text below the avatar
    draw = ImageDraw.Draw(background)
    try:
        font1 = ImageFont.truetype("arial-bold.ttf", 90)
        font2 = ImageFont.truetype("arial.ttf", 70)
    except:
        font = ImageFont.load_default()

    # Use default line2 if not provided
    if line2 is None:
        line2 = f"{member.name}!"
    
    # Calculate text positions (centered below avatar)
    line1_bbox = draw.textbbox((0, 0), line1, font=font1)
    line1_width = line1_bbox[2] - line1_bbox[0]
    line1_x = (bg_width - line1_width) // 2  # Center horizontally
    line2_bbox = draw.textbbox((0, 0), line2, font=font2)
    line2_width = line2_bbox[2] - line2_bbox[0]
    line2_x = (bg_width - line2_width) // 2  # Center horizontally

    # Position text below avatar with spacing
    text_y_start = avatar_y + avatar_size + 50  # Start 20px below avatar
    line_spacing = 125  # Distance between lines (adjust as needed)
    draw.text((line1_x, text_y_start), line1, fill=(255, 255, 255), font=font1)
    draw.text((line2_x, text_y_start + line_spacing), line2, fill=(255, 255, 255), font=font2)

    return background

#@tasks.loop(hours=24)  # Runs every 24 hours
@tasks.loop(seconds=10)  # For testing; revert to hours=24 for production
async def check_roles():
    for guild in bot.guilds:
        async for member in guild.fetch_members(limit=None):
            if not member.bot:
                # Role cleanup
                if PATREON_ROLE not in [role.id for role in member.roles]:
                    milestone_role_ids = list(MILESTONE_ROLES.values())
                    roles_to_remove = [role for role in member.roles if role.id in milestone_role_ids]
                    if roles_to_remove:
                        await member.remove_roles(*roles_to_remove)
                        print(f'Removed milestone roles from {member.name}')

                # Role assignment
                if PATREON_ROLE in [role.id for role in member.roles]:
                    join_date = member_data.get(str(member.id), {}).get('join_date')
                    if not join_date:
                        continue

                    days_on_server = (datetime.now().timestamp() - join_date) // (60 * 60 * 24)
                    correct_role_id = None
                    milestone_key = None

                    if days_on_server >= 1095:
                        correct_role_id = MILESTONE_ROLES['3years']
                        role_key = '3 Year Member'
                        milestone_key = '3years'
                    elif days_on_server >= 730:
                        correct_role_id = MILESTONE_ROLES['2years']
                        role_key = '2 Year Member'
                        milestone_key = '2years'
                    elif days_on_server >= 365:
                        correct_role_id = MILESTONE_ROLES['1year']
                        role_key = '1 Year Member'
                        milestone_key = '1year'
                    elif days_on_server >= 180:
                        correct_role_id = MILESTONE_ROLES['6months']
                        role_key = '6 Month Member'
                        milestone_key = '6months'
                    elif days_on_server >= 90:
                        correct_role_id = MILESTONE_ROLES['3months']
                        role_key = '3 Month Member'
                        milestone_key = '3months'
                    elif days_on_server <= 89:
                        correct_role_id = MILESTONE_ROLES['newmember']
                        role_key = 'New Member'
                        milestone_key = 'newmember'

                    current_milestone_ids = [role.id for role in member.roles if role.id in MILESTONE_ROLES.values()]
                    has_correct_role = correct_role_id in [role.id for role in member.roles]

                    if correct_role_id and not has_correct_role:
                        # Remove incorrect milestone roles
                        roles_to_remove = [role for role in member.roles if role.id in current_milestone_ids]
                        if roles_to_remove:
                            await member.remove_roles(*roles_to_remove)

                        # Define role_to_add before using it
                        role_to_add = guild.get_role(correct_role_id)

                        if not role_to_add:
                            print(
                                f"Role ID {correct_role_id} not found in guild "
                                f"{guild.name} ({guild.id})"
                            )
                            continue  # Skip this member safely

                        await member.add_roles(role_to_add)


                        # Get the appropriate channel for this milestone
                        channel_id = MILESTONE_CHANNELS.get(milestone_key)
                        channel = guild.get_channel(channel_id)

                        # Announcement logic
                        if channel:
                            print(f"Found channel for {milestone_key}: {channel.name}")
                            if channel.permissions_for(guild.me).send_messages:
                                if milestone_key == 'newmember':
                                    # Send new member message with image to WELCOME_CHANNEL
                                    welcome_image = await create_background_image(
                                        member,
                                        line1= f"Welcome {member.name}",
                                        line2= "Everyone give them a warm welcome!")
                                    with io.BytesIO() as image_binary:
                                        welcome_image.save(image_binary, "PNG")
                                        image_binary.seek(0)
                                        await channel.send(
                                             f"{member.mention}! 🎉",
                                            file=discord.File(fp=image_binary, filename="welcome.png")
                                        )
                                else:
                                    # Send milestone-specific message
                                    milestone_image = await create_background_image(
                                        member,
                                        line1= f"Congrats {member.name}!",
                                        line2= f"You are now a {role_key}",
                                        role_name=role_key
                                    )
                                    with io.BytesIO() as image_binary:
                                        milestone_image.save(image_binary, "PNG")
                                        image_binary.seek(0)
                                        await channel.send(
                                            f"{member.mention} <@&{correct_role_id}> 🎉🏆",
                                            file=discord.File(fp=image_binary, filename="milestone.png")
                                        )
                            else:
                                print(f"Bot lacks Send Messages permission in {channel.name}!")
                        else:
                            print(f"Channel for milestone {milestone_key} not found!")
# Run the bot
bot.run(TOKEN)