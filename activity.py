import sys
import database
import discord
import yaml
import logging
import datetime
import send_dm
from typing import Optional

# Load the config
yaml_filename = "config_local.yaml"
cfg = yaml.safe_load(open(yaml_filename))

# Here are activity roles we have.
# It's a hardcoded assumption across this whole file
# that there are exactly these three different activity roles
osallistuja_role_id = cfg["osallistuja_role_id"]
lukija_role_id = cfg["lukija_role_id"]
aktiivi_role_id = cfg["aktiivi_role_id"]

# The jäsen role is manually assigned by moderators. It's not
# considered an "activity role". Having the jäsen role is a prerequisite
# for getting an activity role.
jasen_role_id = cfg["jasen_role_id"]

def get_activity_role_id(message_count: int, is_jasen: bool) -> discord.Role:
    if not is_jasen or message_count < 3: return lukija_role_id 
    elif message_count < 10: return osallistuja_role_id
    else: return aktiivi_role_id

def get_current_activity_role_ids(guild: discord.Guild, member: discord.Member) -> set[int]:
    # Get activity role objects that the user has
    activity_roles = filter(lambda r : r.id in [aktiivi_role_id, osallistuja_role_id, lukija_role_id], member.roles)

    # Return the ids
    return set(map(lambda r : r.id, activity_roles))
    
# May return None if member not found
def get_member_by_id(guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
    member = guild.get_member(user_id) # Get cached member object, can be None
    if member == None: # Try to get the member with an API call
        print("Warning: error fetching member", user_id)
    return member

# Returns true if the roles were changed (and they were not correct already)
async def set_activity_role(guild: discord.Guild, member: discord.Member, role_id : int) -> bool:
    assert(role_id == aktiivi_role_id or role_id == osallistuja_role_id or role_id == lukija_role_id)

    current_activity_roles = get_current_activity_role_ids(guild,member)
    if len(current_activity_roles) == 0:
        print("WARNING: USER {} HAS NO ACTIVITY ROLE!!".format(member.name))
    
    if current_activity_roles != set([role_id]):
        print("Setting", member.name, "to", role_id)

        await member.add_roles(guild.get_role(role_id))

        # Keep activity roles mutually exclusive
        if role_id == osallistuja_role_id:
            await member.remove_roles(guild.get_role(lukija_role_id), guild.get_role(aktiivi_role_id))
        elif role_id == lukija_role_id:
            await member.remove_roles(guild.get_role(osallistuja_role_id), guild.get_role(aktiivi_role_id))
        elif role_id == aktiivi_role_id:
            await member.remove_roles(guild.get_role(osallistuja_role_id), guild.get_role(lukija_role_id))
        return True

    return False # No change to roles

async def process_member(guild: discord.Guild, member: discord.Member, message_count):
    is_jasen = any([role.id == jasen_role_id for role in member.roles])

    new_activity_role_id = get_activity_role_id(message_count, is_jasen)
    roles_changed = await set_activity_role(guild, member, new_activity_role_id)
    
    if roles_changed: 
        # Roles have changed. Send a DM to inform the user.
        pass
        #print("Send DM (not actually sending)", member.name)
        #if user_id == 274591752969781250: # Drai (testing)
        #    await send_dm.send_dm(api, user_id, "DM test")
        #  TODO: actually send the DM

# This function calls functions that assume that the data in the cache of the guild object is up to date
async def update_all_users(db_connection, guild, api):
    # - Get the summed up message counts by user id from the database
    # - For each user, change the role according to the message count. Send DM if there were changes.

    cursor = db_connection.cursor()
    cursor.execute("SELECT user_id, sum(count) AS total FROM message_counts GROUP BY user_id")
    message_counts = cursor.fetchall()

    # Find user ids that are in the guild but not in the activity database (0 messages sent in the tracking interval)
    user_ids_not_in_db = set([x.id for x in guild.members]) # Initialize with all users in the guild
    for (user_id, message_count) in message_counts:
        if user_id in user_ids_not_in_db:
            user_ids_not_in_db.remove(user_id)

    # Add entries with zero messages
    for user_id in user_ids_not_in_db:
        message_counts.append((user_id, 0)) # Zero messages

    # Update roles for all users
    for (user_id, message_count) in message_counts:
        member = get_member_by_id(guild, user_id)
        if member == None: 
            print("User", user_id, "not found") # Probably has left the guild but is still in the db
        else:
            await process_member(guild, member, message_count)
        

        
def clean_up_activity_database(db_connection, days_to_keep):
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep) # Older than this will be deleted

    print("Deleting message counts before date", cutoff_date)
    cursor = db_connection.cursor()
    cursor.execute("DELETE FROM message_counts WHERE date < %s", [cutoff_date])
    print("Deleted",cursor.rowcount,"rows")

    db_connection.commit()


##
## Start the client
##

# Set to remember if the client is already running, since on_ready may be called
# more than once on reconnects
this = sys.modules[__name__]
this.running = False

# Initialize the client using the class discord.Client instead of discord.Bot because otherwise we register as a slash
# command handler, and if there is another script running, then this script tries to handle half
# of the slash commands? Which breaks slash commands since we have not set up the handlers here.
print("Starting up...")
client = discord.Client(intents=discord.Intents(message_content=True, guild_messages=True, guilds=True, messages=True, members=True))

connection_pool = database.open_database(cfg["db_name"], cfg["db_user"], cfg["db_password"])

# Define event handlers for the client
# on_ready may be called multiple times in the event of a reconnect,
# hence the running flag
@client.event
async def on_ready():
    if this.running: return
    else: this.running = True

    print("Bot started up.", flush=True)
    print(client.guilds)
    print(len(client.guilds))
    for guild in client.guilds:
        clean_up_activity_database(connection_pool.get_connection(), 90)
        await update_all_users(connection_pool.get_connection(), guild, client)
    print("FINISHED")
    await client.close()

client.run(cfg["token"])

