import sys
import database
import discord
import yaml
import logging
from typing import Optional

# TODO: put these to a config file
aktiivi_role_id = 1203348797368049704
osallistuja_role_id = 1203348855534526474
jasen_role_id = 520963751478820875 # "jäsen"

def get_activity_role_id(message_count: int, is_jasen: bool) -> Optional[discord.Role]:
    if not is_jasen: return None # Non-members can't have activity roles

    if message_count >= 10: # "Aktiivi"
        return aktiivi_role_id
    elif message_count >= 3: # "Osallistuja"
        return osallistuja_role_id
    else:
        return None
    
# May return None if member not found
async def get_member_by_id(guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
    member = guild.get_member(user_id) # Get cached member object, can be None
    if member == None: # Try to get the member with an API call
        try:
            member = await guild.fetch_member(user_id)
        except:
            print("Warning: error fetching member", user_id)
            return None
    return member

async def set_activity_role(guild: discord.Guild, member: discord.Member, role_id : Optional[int]):
    assert(role_id == None or role_id == aktiivi_role_id or role_id == osallistuja_role_id)
    print("Setting", member.name, "to", role_id)

    if role_id == None:
       await member.remove_roles(guild.get_role(osallistuja_role_id))
       await member.remove_roles(guild.get_role(aktiivi_role_id))
    else: 
        await member.add_roles(guild.get_role(role_id))

        # Keep activity roles mutually exclusive
        if role_id == aktiivi_role_id:
            await member.remove_roles(guild.get_role(osallistuja_role_id))
        elif role_id == osallistuja_role_id:
            await member.remove_roles(guild.get_role(aktiivi_role_id))

async def process_member(guild: discord.Guild, member: discord.Member, message_count):
    is_jasen = any([role.id == jasen_role_id for role in member.roles])
    new_activity_role_id = get_activity_role_id(message_count, is_jasen) # Can be None
    await set_activity_role(guild, member, new_activity_role_id)

async def update_roles(db_connection, guild, api):
    # - Get the summed up message counts by user id from the database
    # - For each user, change the role according to the message count. Send DM if there were changes.

    cursor = db_connection.cursor()
    cursor.execute("SELECT user_id, sum(count) AS total FROM message_counts GROUP BY user_id")
    message_counts = cursor.fetchall()

    for (user_id, message_count) in message_counts:
        member = await get_member_by_id(guild, user_id)
        if member == None: 
            print("User", user_id, "not found") # Has left the guild?
        else:
            await process_member(guild, member, message_count)

    # TODO: DM user
        
def clean_up_activity_database(db_connection, days_to_keep):
    pass


# "MAIN FUNCTION" below

logging.basicConfig(level=logging.INFO)

# Set to remember if the bot is already running, since on_ready may be called
# more than once on reconnects
this = sys.modules[__name__]
this.running = False

yaml_filename = "config_local.yaml"
configs = yaml.safe_load(open(yaml_filename))
cfg = configs["instances"][520938302946148367] # Polymoaria Suomi guild id

# Initialize the bot
print("Starting up...")
bot = discord.Bot(intents=discord.Intents(message_content=True, guild_messages=True, guilds=True, messages=True, members=True))

connection_pool = database.open_database(cfg["db_name"], cfg["db_user"], cfg["db_password"])

# Define event handlers for the bot
# on_ready may be called multiple times in the event of a reconnect,
# hence the running flag
@bot.event
async def on_ready():
    if this.running: return
    else: this.running = True

    print("Bot started up.", flush=True)
    print(bot.guilds)
    print(len(bot.guilds))
    for guild in bot.guilds:
        if guild.name == "Polyamoria Suomi":
            await update_roles(connection_pool.get_connection(), guild, bot)

bot.run(configs["token"])
