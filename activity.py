import sys
import database
import discord
import yaml
import logging

# TODO: put these to a config file
aktiivi_role_id = 1203348797368049704
osallistuja_role_id = 1203348855534526474
hiljainen_role_id = 1203348933791719475

def get_activity_role_id(message_count: int):
    if message_count >= 10: # "Aktiivi"
        return aktiivi_role_id
    elif message_count >= 3: # "Osallistuja"
        return osallistuja_role_id
    else: # Hiljainen
        return hiljainen_role_id
    

async def update_roles(db_connection, guild, api):
    # - Get the summed up message counts by user id from the database
    # - For each user, change the role according to the message count. Send DM if there were changes.

    cursor = db_connection.cursor()
    cursor.execute("SELECT user_id, sum(count) AS total FROM message_counts GROUP BY user_id")
    winners = cursor.fetchall()

    for (user_id, message_count) in winners:
        new_role_id = get_activity_role_id(message_count)
        new_role = guild.get_role(new_role_id)
    
        member = guild.get_member(user_id) # Get cached member objec5
        #if member == None: # Try to get the member with an API call
        #    member = await guild.fetch_member(user_id)
        if member == None:
            print("Member", user_id, "not found")
            continue
        
        print(user_id, member.name, new_role_id, new_role)

        # Assign new role (does nothing if already had this role?)
        await member.add_roles(new_role) 
        continue

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
