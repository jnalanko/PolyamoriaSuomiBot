import sys
import database
import discord
import yaml
import logging

# TODO: put these to a config file
aktiivi_role_id = 1203348797368049704
osallistuja_role_id = 1203348855534526474
hiljainen_role_id = 1203348933791719475

def get_activity_role(message_count: int):
    if message_count >= 10: # "Aktiivi"
        return aktiivi_role_id
    elif message_count >= 3: # "Osallistuja"
        return osallistuja_role_id
    else: # Hiljainen
        return hiljainen_role_id
    

async def update_roles(db_connection, api):
    # - Get the summed up message counts by user id from the database
    # - For each user, change the role according to the message count. Send DM if there were changes.

    cursor = conn.cursor()
    cursor.execute("SELECT user_id, sum(count) AS total FROM message_counts GROUP BY user_id")
    winners = cursor.fetchall()

    for (user_id, message_count) in winners:
        new_role = get_activity_role(message_count)
        print(user_id, new_role)
        return # DEBUG

        user = await api.fetch_user(user_id)

        # Assign new role (does nothing if already had this role?)
        user.add_roles(new_role) 

        # Remove old role (activity roles are mutually exclusive)
        if new_role != aktiivi_role_id:
            user.remove_roles(aktiivi_role_id)
        if new_role != osallistuja_role_id:
            user.remove_roles(osallistuja_role_id)
        if new_role != hiljainen_role_id:
            user.remove_roles(hiljainen_role_id)

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
global_config = yaml.safe_load(open(yaml_filename))
print("Global config:", global_config)

# Initialize the client
print("Starting up...")
client = discord.Client(intents=discord.Intents(message_content=True, guild_messages=True, guilds=True, messages=True, members=True))

connection_pool = database.open_database(db_name, db_user, db_password)

# Define event handlers for the client
# on_ready may be called multiple times in the event of a reconnect,
# hence the running flag
@client.event
async def on_ready():
    if this.running: return
    else: this.running = True

    print("Bot started up.", flush=True)
    print(client.guilds)
    for guild in client.guilds:
        if guild.name == "Polyamoria Suomi":
            await update_roles(guild, connection_pool.get_connection())

client.run(global_config["token"])