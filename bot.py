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

logging.basicConfig(level=logging.INFO)

class AutoDeleteCallBack:

    # Returns whether the message was deleted
    async def process_message(self, msg):
        if msg.pinned == False and not msg.is_system(): # Skip pinned and system messages
            try: 
                await msg.delete()
                return True
            except Exception as e:
                print("Error deleting message: " + str(e))
                return False
        return False

    async def run(self, client, delete_older_than_minutes, channel_name, log_channel_name, guild_id):

        # Find the log channel
        log_channel = None
        guild = client.get_guild(guild_id)
        
        for channel in guild.channels:
            if channel.name == log_channel_name:
                log_channel = channel # todo: what if not found?

        # Run autodelete
        for channel in guild.channels:
            if channel.name == channel_name:
                prev_time = datetime.now(pytz.utc)  - timedelta(minutes=delete_older_than_minutes)

                # Autodelete in channel
                n_deleted = 0
                async for msg in channel.history(before = prev_time, oldest_first = True, limit = None):
                    print("Processing message on channel {}: {}".format(channel.name, msg.system_content))
                    success = await self.process_message(msg)
                    if(success): n_deleted += 1
                    else:
                        print("Did not delete message: {}".format(msg.system_content))
                await log_channel.send("Poistin kanavalta **#{}** viestit ennen ajanhetkeä {} UTC (yhteensä {} viestiä)".format(channel_name, prev_time.strftime("%Y-%m-%d %H:%M:%S"), n_deleted))

                # Autodelete in threads under this channel
                all_threads = channel.threads
                async for T in channel.archived_threads(limit=None):
                    all_threads.append(await T.unarchive()) # Unarchive because we can't delete messages from archived threads
                print("Channel {} has threads {}".format(channel.name, str([t.name for t in all_threads])))
                for thread in all_threads:
                    n_deleted = 0
                    async for msg in thread.history(before = prev_time, oldest_first = True, limit = None):
                        print("Processing message in thread {}: {}".format(thread.name, msg.system_content))
                        success = await self.process_message(msg)
                        if(success): n_deleted += 1
                        else:
                            print("Did not delete message: {}".format(msg.system_content))
                    await log_channel.send("Poistin ketjusta **#{}** viestit ennen ajanhetkeä {} UTC (yhteensä {} viestiä)".format(thread.name, prev_time.strftime("%Y-%m-%d %H:%M:%S"), n_deleted))


# An object of this class manages the bot for *one* server.
class MyBot:

    def __init__(self, instance_config, guild_id):
        print("Instance config:", instance_config)
        self.guild_id = guild_id
        self.autodel_config = instance_config["autodelete_channels"] # List of dicts {channel: X, callback_interval_minutes: Y, delete_older_than_minutes: Z] (todo: make channel a key)
        self.sched = AsyncIOScheduler()
        self.autodelete = AutoDeleteCallBack()
        self.jobs = dict() # channel name -> job
        self.log_channel_name = "bottikomennot" # todo: configiin?
        
    # Updates config and the affected job. If no job is yet active, creates a new job
    def set_autodel(self, channel_name, callback_interval_minutes, delete_older_than_minutes): # returns new autodel config
        # Check if autodelete is already active for the channel and if so, update config the values
        existing = False
        for i in range(len(self.autodel_config)):
            if self.autodel_config[i]["channel"] == channel_name:
                self.autodel_config[i]["callback_interval_minutes"] = callback_interval_minutes
                self.autodel_config[i]["delete_older_than_minutes"] = delete_older_than_minutes
                existing = True

        # Autodelete is not yet active for this channel
        if not existing:
            # Add new entry to the config
            self.autodel_config.append({"channel": channel_name, "callback_interval_minutes": callback_interval_minutes, "delete_older_than_minutes": delete_older_than_minutes})

        self.create_job(channel_name, callback_interval_minutes, delete_older_than_minutes) # Create new job

        print("Autodel config is now:", self.autodel_config)
        return self.autodel_config

    # Updates config and removes the affected job (if exists)
    def remove_autodel_from_channel(self, channel_name):
        for i in range(len(self.autodel_config)):
            if self.autodel_config[i]["channel"] == channel_name:
                del self.autodel_config[i]
                break
        if channel_name in self.jobs: 
            self.jobs[channel_name].remove()
            del self.jobs[channel_name]
        return self.autodel_config

    # Does not update config
    def create_job(self, channel_name, callback_interval_minutes, delete_older_than_minutes):
        if channel_name in self.jobs:
            self.jobs[channel_name].remove() # Terminate existing job

        self.jobs[channel_name] = self.sched.add_job(self.autodelete.run, 'interval', (client, delete_older_than_minutes, channel_name, self.log_channel_name, self.guild_id), minutes=callback_interval_minutes)

    def startup(self):
        print("Adding all jobs and starting the scheduler.")
        self.add_all_jobs()
        self.sched.start()

    def add_all_jobs(self):
        print("Adding all jobs")
        for X in self.autodel_config:
            print("Adding " + str(X))
            self.create_job(X["channel"], X["callback_interval_minutes"], X["delete_older_than_minutes"])
        print(self.jobs)

    def trigger_all_jobs_now(self):
        print("Triggering all jobs")
        for channel_name in self.jobs:
            print("Trigger", channel_name)
            self.jobs[channel_name].modify(next_run_time=datetime.now())

    def get_settings_string(self):
        lines = []
        lines.append("**Autodelete-asetukset**")
        for job in self.autodel_config:
            lines.append("**#{}**: Poistan {} tunnin välein vähintään {} päivää vanhat viestit.".format(job["channel"], job["callback_interval_minutes"]//60, job["delete_older_than_minutes"]//(60*24)))
        return "\n".join(lines)

# Todo: Use channel objects instead of channel names

# Set to remember if the bot is already running, since on_ready may be called
# more than once on reconnects
this = sys.modules[__name__]
this.running = False

yaml_filename = "config_local.yaml"
global_config = yaml.safe_load(open(yaml_filename))
print("Global config:", global_config)

instances = dict() # Guild id -> MyBot object

# Initialize the client
print("Starting up...")
client = discord.Client(intents=discord.Intents(message_content=True, guild_messages=True, guilds=True, messages=True))

# Define event handlers for the client
# on_ready may be called multiple times in the event of a reconnect,
# hence the running flag
@client.event
async def on_ready():
    if this.running: return
    else: this.running = True

    
    print("Bot started up.", flush=True)
    async for guild in client.fetch_guilds(limit=150):
        print("guild", guild.name, guild.id)

        if guild.id not in global_config["instances"]:
            global_config["instances"][guild.id] = {"autodelete_channels": []} # Init empty config for this guild

        instance = MyBot(global_config["instances"][guild.id], guild.id) # todo: this is a bit silly
        instance.startup()
        instances[guild.id] = instance
    print(instances)

async def admin_commands(message):
    mybot = instances[message.guild.id]
    if message.content.startswith("!") and message.channel.name == "bottikomennot":
        if message.content.startswith("!ohjeet"):
            lines = []
            lines.append("**PolyamoriaSuomiBot**")
            lines.append("")
            lines.append("Komento **!ohjeet** tulostaa tämän käyttöohjeen. Komento **!asetukset** näyttää nykyiset asetukset. Muita komentoja ovat:")
            lines.append("")
            lines.append("**!autodelete** aseta [kanavan nimi ilman risuaitaa] [aikahorisontti päivinä] [kuinka monen tunnin välein poistot tehdään]")
            lines.append("**!autodelete** aja-nyt")
            lines.append("**!autodelete** lopeta [kanavan nimi]")
            lines.append("")
            lines.append("Esimerkiksi jos haluat asettaa kanavan #mielenterveys poistoajaksi 60 päivää siten, että poistot tehdään kerran päivässä, anna kirjoita komentokanavalle komento `!autodelete aseta mielenterveys 90 24`. Annetuiden numeroiden on oltava kokonaislukuja. Tällä komennolla voi myös muokata olemassaolevia asetuksia kanavalle. Jos haluat myöhemmin ottaa poiston pois päältä, anna komento `!autodelete lopeta mielenterveys`.")
            await message.channel.send("\n".join(lines))
        elif message.content.startswith("!asetukset"):
            await message.channel.send(mybot.get_settings_string())
        elif message.content.startswith("!autodelete aja-nyt"):
            await message.channel.send("Ok, ajetaan kaikki autodeletoinnit nyt.")
            mybot.trigger_all_jobs_now()
        elif message.content.startswith("!autodelete lopeta"):
            tokens = message.content.split()
            
            # Check the number of parameters
            if len(tokens) != 3:
                await message.channel.send("Virhe: Väärä määrä parametreja. Komennolle `!autodelete lopeta` täytyy antaa yksi parametri.")
                return

            # Check that the channel exists
            channel_name = tokens[2]
            if not (channel_name in [C.name for C in message.guild.channels]):
                await message.channel.send("Virhe: Kanavaa #{} ei ole olemassa tai minulla ei ole oikeuksia siihen.".format(channel_name))
                return

            # Run the command
            global_config["instances"][message.guild.id]["autodelete_channels"] = mybot.remove_autodel_from_channel(channel_name)
            await message.channel.send("Autodelete lopetettu kanavalta " + channel_name)

            # Update config file
            with open(yaml_filename, 'w') as outfile:
                yaml.dump(global_config, outfile, default_flow_style=False)
            print("Updated config file", yaml_filename)

        elif message.content.startswith("!autodelete aseta"):
            tokens = message.content.split()

            # Check the number of parameters
            if len(tokens) != 5:
                await message.channel.send("Virhe: Väärä määrä parametreja. Komennolle `!autodelete aseta` täytyy antaa kolme parametria.")
                return

            # Check the parameter types
            try:
                channel_name, time_horizon_days, interval_hours = tokens[2], int(tokens[3]), int(tokens[4])
                if time_horizon_days < 1 or interval_hours < 1:
                    raise ValueError("Time parameter not positive")
            except ValueError:
                await message.channel.send("Virhe: Vääränlaiset parametrit. Komennolle `!autodelete aseta` täytyy antaa kanavan nimi ja kaksi positiivista kokonaislukua.")
                return

            # Check that the channel exists
            if not (channel_name in [C.name for C in message.guild.channels]):
                await message.channel.send("Virhe: Kanavaa #{} ei ole olemassa tai minulla ei ole oikeuksia siihen.".format(channel_name))
                return

            # Run the command
            global_config["instances"][message.guild.id]["autodelete_channels"] = mybot.set_autodel(channel_name, interval_hours*60, time_horizon_days*60*24)

            # Print the new settings to channel
            await message.channel.send("Poistan kanavalta {} yli {} päivää vanhat viestit {} tunnin välein".format(channel_name, time_horizon_days, interval_hours))
        else:
            await message.channel.send("Tuntematon komento: " + message.content.split()[0])
        # Update config file
        with open(yaml_filename, 'w') as outfile:
            yaml.dump(global_config, outfile, default_flow_style=False)
        print("Updated config file", yaml_filename)

def to_positive_integer(string, upto):
    if not string.isdigit():
        raise ValueError("Syntaksivirhe: " + string)
    if int(string) <= 0:
        raise ValueError("Virhe: Ei-positiivinen numero: " + string)
    if int(string) > upto:
        raise ValueError("Virhe: Liian iso numero: " + string)
    return int(string)

# Returns the result as a string
def do_roll(expression):
    rolls = []
    sum_of_constants = 0

    expression = expression.replace("+", " + ").replace("-", " - ")

    sign = 1 # +1 or -1

    try: 
        tokens = expression.split()
        if len(tokens) == 0:
            return "Anna heitto muodossa 2d6 + 5"
        if len(tokens) > 20:
            return "Liian monta operaatiota"
        for i, token in enumerate(tokens):
            token = token.strip()
            if i % 2 == 1:
                if token == '+': sign = 1
                elif token == '-': sign = -1
                else: raise ValueError("Syntaksivirhe: " + token)
            else:
                if token.count("d") == 0:
                    # Constant
                    sum_of_constants += int(to_positive_integer(token, 1e6)) * sign
                elif token.count("d") == 1:
                    # Dice
                    n_dice, n_sides = token.split('d')
                    if n_dice == "": n_dice = "1" # Implicit 1
                    n_dice = to_positive_integer(n_dice, 100)
                    n_sides = to_positive_integer(n_sides, 1e6)
                    while n_dice > 0:
                        rolls.append(random.randint(1,n_sides) * sign)
                        n_dice -= 1
                else:
                    raise ValueError("Syntaksivirhe: " + token)
    except ValueError as e: return str(e)

    if sum_of_constants != 0: 
        message = "{} + {} = {}".format(rolls, sum_of_constants, sum(rolls) + sum_of_constants)
    else:
        message = "{} = {}".format(rolls, sum(rolls))
    if len(message) > 1000: return "Liian monta heittoa"
    else: return message



@client.event
async def on_message(message):
    print("onmessage", message.content)
    mybot = instances[message.guild.id]

    await admin_commands(message)

    if message.content.startswith("!roll"):
        expression = message.content[5:].strip()
        try:
            result = konso_dice_roller.markdown_roll_string_from_input(expression, number_of_dice_limit=100, dice_sides_limit=10**6, bonus_absolute_value_limit=10**6)
            await message.channel.send(message.author.name + " heitti " + result)
        except Exception as e:
            await message.channel.send(message.author.name + " heitti `" + expression + "`. Virhe: " + str(e))

    elif message.content.startswith("!vanharoll"):
        expression = message.content[10:].strip()
        result = do_roll(expression)
        await message.channel.send(message.author.name + " heitti `" + expression.strip() + "`, tulos: `" + result + "`")
    


client.run(global_config["token"])
