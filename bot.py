import sys

import discord
import yaml

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from multiprocessing                import Process
from datetime import datetime, timedelta

class AutoDeleteCallBack:
    async def run(self, client, delete_older_than_minutes, active_channel_names):
        for channel in client.get_all_channels():
            if channel.name in active_channel_names:
                prev_time = datetime.utcnow() - timedelta(minutes=delete_older_than_minutes)
                async for elem in channel.history(before = prev_time):
                    await elem.delete()

# Set to remember if the bot is already running, since on_ready may be called
# more than once on reconnects
this = sys.modules[__name__]
this.running = False

# Scheduler that will be used to manage events
sched = AsyncIOScheduler()

print("Loading config")
config = yaml.safe_load(open("config.yaml"))
token = config["token"]
callback_interval = config["callback_interval_minutes"]
delete_older_than_minutes = config["delete_older_than_minutes"]
active_channel_names = config["active_channels"]

print("Deleting every {} minutes all messages older than {} minutes from these channels: {}".format(callback_interval, delete_older_than_minutes, str(active_channel_names)))

autodelete = AutoDeleteCallBack()

# Initialize the client
print("Starting up...")
client = discord.Client()

# Define event handlers for the client
# on_ready may be called multiple times in the event of a reconnect,
# hence the running flag
@client.event
async def on_ready():
    if this.running: return
    else: this.running = True

    print("Logged in. Setting up callbacks.", flush=True)
    sched.add_job(autodelete.run, 'interval', (client, delete_older_than_minutes, active_channel_names), minutes=callback_interval)
    sched.start()
    print(f"Setup finished. Running.", flush=True)

client.run(token)
