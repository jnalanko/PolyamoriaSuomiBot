import sys

import discord
import yaml
import logging
import random
from mybot import MyBot
from send_dm import send_dm

import mysql.connector

import konso_dice_roller.konso_dice_roller as konso_dice_roller

logging.basicConfig(level=logging.INFO)

# Set to remember if the bot is already running, since on_ready may be called
# more than once on reconnects
this = sys.modules[__name__]
this.running = False

yaml_filename = "config_local.yaml"
config = yaml.safe_load(open(yaml_filename))
print("Config config:", config)

instances = dict() # Guild id -> MyBot object

# Initialize the client
print("Starting up...")
# open_database(config["db_name"], config["db_user"], config["db_password"])
client = discord.Client(intents=discord.Intents(message_content=True, guild_messages=True, guilds=True, messages=True, members=True))

# Define event handlers for the client
# on_ready may be called multiple times in the event of a reconnect,
# hence the running flag
@client.event
async def on_ready():
    if this.running: return
    else: this.running = True

    print("Client started up.", flush=True)
    for guild_id in config["instances"]:
        cfg = config["instances"][guild_id]
        instance = MyBot(guild_id, cfg["db_name"], cfg["db_user"], cfg["db_password"], cfg["admin_user_id"], client)

        instance.startup()
        instances[guild_id] = instance

    print(instances)


# TODO: separate DBs for different guilds. What is an "instance" the bot anyway?
# An instance should read only from its own database.

@client.event
async def on_message(message):
    print("onmessage", message.content)
    if message.guild == None:
        return # DM?

    if not message.guild.id in instances:
        admin = config["master_admin_user_id"]
        send_dm(client, admin, "Got message from guild {} but no instance defined for that guild".format(message.guild.id))
        return 
        
    mybot = instances[message.guild.id]
    mybot.process_message(message)

client.run(config["token"])
