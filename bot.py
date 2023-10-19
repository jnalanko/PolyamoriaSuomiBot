import sys

import discord
import yaml
import logging
from mybot import MyBot
from send_dm import send_dm

logging.basicConfig(level=logging.INFO)

# Set to remember if the bot is already running, since on_ready may be called
# more than once on reconnects
this = sys.modules[__name__]
this.running = False

yaml_filename = "config_local.yaml"
config = yaml.safe_load(open(yaml_filename))
guild_ids = list(config["instances"].keys())
print("Config:", config)

instances = dict() # Guild id -> MyBot object

# Initialize the client
print("Starting up...")
# open_database(config["db_name"], config["db_user"], config["db_password"])
bot = discord.Bot(intents=discord.Intents(message_content=True, guild_messages=True, guilds=True, messages=True, members=True))

# Define event handlers for the client
# on_ready may be called multiple times in the event of a reconnect,
# hence the running flag
@bot.event
async def on_ready():
    if this.running: return
    else: this.running = True

    print("Client started up.", flush=True)
    for guild_id in config["instances"]:
        cfg = config["instances"][guild_id]
        instance = MyBot(guild_id, cfg["bot_channel_id"], cfg["midnight_channel_id"], cfg["db_name"], cfg["db_user"], cfg["db_password"], cfg["admin_user_id"], bot)

        instance.startup()
        instances[guild_id] = instance

    print(instances)

@bot.event
async def on_message(message):
    print("onmessage", message.content)
    if message.guild == None:
        return # DM?

    if not message.guild.id in instances:
        print("Got message from guild {} but no instance defined for that guild".format(message.guild.id))
        return 
        
    mybot = instances[message.guild.id]
    await mybot.process_message(message)

@bot.slash_command(guild_ids=guild_ids, name="midnight-leaderboard", description="Midnight leaderboard")
async def midnight_leaderboard(ctx):
    await instances[ctx.guild_id].midnight_leaderboard_command(ctx)

bot.run(config["token"])
