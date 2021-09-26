import sys

import discord
import yaml

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from multiprocessing                import Process
from datetime import datetime, timedelta

class AutoDeleteCallBack:
    async def run(self, client, delete_older_than_minutes, channel_name):
        for channel in client.get_all_channels():
            if channel.name == channel_name:
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
config = yaml.safe_load(open("config_local.yaml"))
token = config["token"]

autodel_config = config["autodelete_channels"] # Dicts {channel: X, callback_interval_minutes: Y, delete_older_than_minutes: Z]
#print(X["channel"], X["callback_interval_minutes"], X["delete_older_than_minutes"])

print("Config:" + str(config))
#print("Deleting every {} minutes all messages older than {} minutes from these channels: {}".format(callback_interval, delete_older_than_minutes, str(active_channel_names)))

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
    for job in autodel_config:
        sched.add_job(autodelete.run, 'interval', (client, job["delete_older_than_minutes"], job["channel"]), minutes=job["callback_interval_minutes"])
    sched.start()
    print(f"Setup finished. Running.", flush=True)
    for channel in client.get_all_channels():
        for job in autodel_config:
            if channel.name == job["channel"]:
                await channel.send("Botti käynnistyy. Poistan tältä kanavalta {} minuutin välein vähintään {} minuuttia vanhat viestit.".format(job["callback_interval_minutes"], job["delete_older_than_minutes"]))

client.run(token)
