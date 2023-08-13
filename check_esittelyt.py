import sys

import discord
import yaml
import logging
import pytz
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from multiprocessing                import Process
from datetime import datetime, timedelta

import konso_dice_roller.konso_dice_roller as konso_dice_roller

INTRODUCTIONS_CHANNEL_NAME = "esittele-itsesi"
MEMBER_ROLE_NAME = "jäsen"

async def check_esittelyt(guild):

    member_role_id = None
    for role in guild.roles:
        if role.name == MEMBER_ROLE_NAME:
            member_role_id = role.id

    if member_role_id == None:
        print("Unable to find role " + MEMBER_ROLE_NAME)
        return
    else:
        print("Member role id: " + str(member_role_id))

    members = set()
    print(guild.members, " guild members")
    for user in guild.members:
        if user.get_role(member_role_id) != None:
            print("Member " + user.name)
            members.add(user.name)
        else:
            print("Not member " + user.name)

    # Get the introductions channel
    channel = None
    for c in client.get_all_channels():
        if c.name == INTRODUCTIONS_CHANNEL_NAME:
            channel = c

    if channel == None:
        print("Unable to find channel " + INTRODUCTIONS_CHANNEL_NAME)
        return

    # Figure out which users have an introduction
    users_who_have_an_introduction = set()
    async for msg in channel.history(limit = None):
        print(msg)
        users_who_have_an_introduction.add(msg.author.name)

    print("Users with Jäsen-rooli but no message in " + INTRODUCTIONS_CHANNEL_NAME)
    for user in members:
        if user not in users_who_have_an_introduction:
            print(user)

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
            await check_esittelyt(guild)

client.run(global_config["token"])

