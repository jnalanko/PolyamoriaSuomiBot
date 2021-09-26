import sys

import discord
import yaml

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from multiprocessing                import Process
from datetime import datetime, timedelta

class AutoDeleteCallBack:
    async def run(self, client, delete_older_than_minutes, channel_name, log_channel_name):
        # Find the log channel
        log_channel = None
        for channel in client.get_all_channels():
            if channel.name == log_channel_name:
                log_channel = channel

        # Run autodelete
        for channel in client.get_all_channels():
            if channel.name == channel_name:
                prev_time = datetime.utcnow() - timedelta(minutes=delete_older_than_minutes)
                n_deleted = 0
                async for elem in channel.history(before = prev_time):
                    print("Deleting message: " + str(elem))
                    await elem.delete()
                    n_deleted += 1
                await log_channel.send("Poistin kanavalta **#{}** viestit ennen ajanhetkeä {} (yhteensä {} viestiä)".format(channel_name, prev_time.strftime("%Y-%m-%d %H:%M:%S"), n_deleted))

class MyBot:

    def __init__(self, yaml_filename):
        print("Loading config from " + yaml_filename)
        config = yaml.safe_load(open(yaml_filename))
        print("Config:", config)
        self.token = token = config["token"]
        self.autodel_config = config["autodelete_channels"] # List of dicts {channel: X, callback_interval_minutes: Y, delete_older_than_minutes: Z]
        self.sched = AsyncIOScheduler()
        self.autodelete = AutoDeleteCallBack()
        self.log_channel_name = "bottikomennot"
        
    def set_autodel(self, channel_name, callback_interval_minutes, delete_older_than_minutes):
        # Check if autodelete is already active for the channel and if so, update the values
        for X in self.autodel_config:
            if X["channel"] == channel_name:
                X["callback_interval_minutes"] = callback_interval_minutes
                X["delete_older_than_minutes"] = delete_older_than_minutes
                return

        # Autodelete is not yet active for this channel
        self.autodel_config.append({"channel": channel_name, "callback_interval_minutes": callback_interval_minutes, "delete_older_than_minutes": delete_older_than_minutes})

        # Reboot jobs
        self.remove_all_jobs()
        self.add_all_jobs()

    def startup(self):
        print("Adding all jobs and starting the scheduler.")
        self.add_all_jobs()
        self.sched.start()

    def remove_all_jobs(self):
        print("Removing all jobs")
        self.sched.remove_all_jobs()

    def add_all_jobs(self): # todo: restart only the jobs that are affected? Or run first jobs immediately after starting, not after the first interval
        print("Adding all jobs")
        for X in self.autodel_config:
            job = self.sched.add_job(self.autodelete.run, 'interval', (client, X["delete_older_than_minutes"], X["channel"], self.log_channel_name), minutes=X["callback_interval_minutes"])
            job.modify(next_run_time=datetime.now()) # Schedule the first run to be done immediately

    def get_settings_string(self):
        lines = []
        lines.append("**Autodelete-asetukset**")
        for job in self.autodel_config:
            lines.append("**#{}**: Poistan {} tunnin välein vähintään {} päivää vanhat viestit.".format(job["channel"], job["callback_interval_minutes"]//60, job["delete_older_than_minutes"]//(60*24)))
        return "\n".join(lines)

# todo: tallenna asetukset

# Set to remember if the bot is already running, since on_ready may be called
# more than once on reconnects
this = sys.modules[__name__]
this.running = False

mybot = MyBot("config_local.yaml")

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

    mybot.startup()
    print("Bot started up.", flush=True)

@client.event
async def on_message(message):
    print("onmessage", message.content)
    if message.content.startswith("!ohjeet") and message.channel.name == "bottikomennot": # todo: check server also. Otherwise possiblity of cross-server commands.
        lines = []
        lines.append("**PolyamoriaSuomiBot**")
        lines.append("")
        lines.append("Komento **!ohjeet** tulostaa tämän käyttöohjeen. Komento **!asetukset** näyttää nykyiset asetukset. Muita komentoja ovat:")
        lines.append("")
        lines.append("**!autodelete** aseta [kanavan nimi ilman risuaitaa] [aikahorisontti päivinä] [kuinka monen tunnin välein poistot tehdään]")
        lines.append("**!autodelete** lopeta [kanavan nimi]")
        lines.append("")
        lines.append("Esimerkiksi jos haluat asettaa kanavan #mielenterveys poistoajaksi 60 päivää siten, että poistot tehdään kerran päivässä, anna kirjoita komentokanavalle komento `!autodelete aseta mielenterveys 90 24`. Annetuiden numeroiden on oltava kokonaislukuja. Tällä komennolla voi myös muokata olemassaolevia asetuksia kanavalle. Jos haluat myöhemmin ottaa poiston pois päältä, anna komento `!autodelete lopeta mielenterveys`.")
        await message.channel.send("\n".join(lines))
    if message.content.startswith("!asetukset") and message.channel.name == "bottikomennot":
        await message.channel.send(mybot.get_settings_string())
    if message.content.startswith("!autodelete aseta") and message.channel.name == "bottikomennot":
        tokens = message.content.split()

        # Check the number of parameters
        if len(tokens) != 5:
            await message.channel.send("Virhe: Väärä määrä parametreja. Komennolle `!autodelete aseta` täytyy antaa kolme parametria.")
            return

        # Check the parameter types
        try:
            channel_name, time_horizon_days, interval_hours = tokens[2], int(tokens[3]), int(tokens[4])
        except ValueError:
            await message.channel.send("Virhe: Vääränlaiset parametrit. Komennolle `!autodelete aseta` täytyy antaa kanavan nimi ja kaksi kokonaislukua.")
            return

        # Check that the channel exists
        if not (channel_name in [C.name for C in client.get_all_channels()]):
            await message.channel.send("Virhe: Kanavaa #{} ei ole olemassa tai minulla ei ole oikeuksia siihen.".format(channel_name))
            return

        # Run the command
        mybot.set_autodel(channel_name, interval_hours, time_horizon_days) # todo: it says it's hours and minutes but for debug it's actually minutes and minutes

        # Print the new settings
        await message.channel.send(mybot.get_settings_string())

client.run(mybot.token)
