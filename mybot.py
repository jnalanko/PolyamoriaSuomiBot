import sys

import discord
import yaml
import logging
import pytz
import random

from send_dm import send_dm

import mysql.connector

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from multiprocessing                import Process
from datetime import datetime, timedelta

import konso_dice_roller.konso_dice_roller as konso_dice_roller
import roll

def open_database(db_name, username, password):

    db_config = {
        "host": "localhost",
        "user": username,
        "password": password,
    }

    database_connection = mysql.connector.connect(**db_config)
    cursor = database_connection.cursor()

    # cursor.execute does not support sanitized CREATE DATABASE queries.
    # So we just trust our own config and plug in the database name directly.
    cursor.execute("CREATE DATABASE IF NOT EXISTS {}".format(db_name))
    cursor.execute("USE {}".format(db_name))
    
    create_message_times_table = """
    CREATE TABLE IF NOT EXISTS recent_message_times (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255),
        date DATETIME,
        INDEX message_times_index (username)
    )
    """

    cursor.execute(create_message_times_table)

    create_autodelete_table = """
    CREATE TABLE IF NOT EXISTS autodelete (
        channel_id BIGINT UNSIGNED PRIMARY KEY,
        callback_interval_minutes INT,
        delete_older_than_minutes INT
    )
    """

    cursor.execute(create_autodelete_table)

    database_connection.commit()

    return database_connection
    
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

    # api is of type discord.Client
    async def run(self, api, delete_older_than_minutes, channel_id, log_channel_name, guild_id, admin_user_id):

        # Find the log channel
        log_channel = None
        guild = api.get_guild(guild_id)
        
        for channel in guild.channels:
            if channel.name == log_channel_name:
                log_channel = channel # todo: what if not found?

        # Run autodelete
        channel_found = False
        try:
            for channel in guild.channels:
                if channel.id == channel_id:
                    channel_found = True
                    prev_time = datetime.now(pytz.utc)  - timedelta(minutes=delete_older_than_minutes)

                    # Autodelete in channel
                    n_deleted = 0
                    async for msg in channel.history(before = prev_time, oldest_first = True, limit = None):
                        print("Processing message on channel {}: {}".format(channel.name, msg.system_content))
                        success = await self.process_message(msg)
                        if(success): n_deleted += 1
                        else:
                            print("Did not delete message: {}".format(msg.system_content))
                    await log_channel.send("Poistin kanavalta **#{}** viestit ennen ajanhetkeä {} UTC (yhteensä {} viestiä)".format(channel.name, prev_time.strftime("%Y-%m-%d %H:%M:%S"), n_deleted))

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

        except Exception as e:
            # Send the error message to the admin user as a DM
            await send_dm(api, admin_user_id, "Error deleting from channel {}: {}".format(channel, str(e)))

        if not channel_found:
            # Send the error message to the admin user as a DM
            await send_dm(api, admin_user_id, "Error: could not find channel: " + str(channel_id))


# An object of this class manages the bot for *one* server.
class MyBot:

    # api is of type discord.Client
    def __init__(self, guild_id, db_name, db_user, db_password, admin_user_id, api):
        self.guild_id = guild_id
        self.sched = AsyncIOScheduler()
        self.autodelete = AutoDeleteCallBack()
        self.jobs = dict() # channel name -> job
        self.log_channel_name = "bottikomennot" # todo: configiin?
        self.admin_user_id = admin_user_id
        self.guild_id = guild_id
        self.api = api
        self.database_connection = open_database(db_name, db_user, db_password)
        self.number_of_message_times_to_remember = 5 # Todo: to config
        
    # If no job is yet active, creates a new job
    def set_autodel(self, channel_name, callback_interval_minutes, delete_older_than_minutes): # returns new autodel config

        # TODO use the database.
        return 

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

        # TODO use the database.
        return 

        for i in range(len(self.autodel_config)):
            if self.autodel_config[i]["channel"] == channel_name:
                del self.autodel_config[i]
                break
        if channel_name in self.jobs: 
            self.jobs[channel_name].remove()
            del self.jobs[channel_name]
        return self.autodel_config

    # Does not update config
    def create_job(self, channel_id, callback_interval_minutes, delete_older_than_minutes):
        if channel_id in self.jobs:
            self.jobs[channel_id].remove() # Terminate existing job

        self.jobs[channel_id] = self.sched.add_job(self.autodelete.run, 'interval', (self.api, delete_older_than_minutes, channel_id, self.log_channel_name, self.guild_id, self.admin_user_id), minutes=callback_interval_minutes)

    def startup(self):
        print("Adding all jobs and starting the scheduler.")
        self.add_all_jobs()
        self.sched.start()

    def add_all_jobs(self):
        print("Adding all jobs")
        cursor = self.database_connection.cursor()
        cursor.execute("SELECT * FROM autodelete")
        for (channel_id, callback_interval_minutes, delete_older_than_minutes) in cursor.fetchall():
            print("Adding autodelete job for channel", channel_id)
            self.create_job(channel_id, callback_interval_minutes, delete_older_than_minutes)
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
        
    def add_message_to_db(self, username):

        cursor = self.database_connection.cursor()

        # Get all rows with the given username sorted by date
        cursor.execute("SELECT * FROM recent_message_times WHERE username = %s ORDER BY date DESC", [username])
        nrows = len(cursor.fetchall())

        # Delete old rows if needed
        number_to_delete = max(nrows - (self.number_of_message_times_to_remember - 1), 0)
        if number_to_delete > 0:
            # Delete the oldest rows
            cursor.execute("DELETE FROM recent_message_times WHERE username = %s ORDER BY date LIMIT %s", [username, number_to_delete])

        # Add the new message
        cursor.execute("INSERT INTO recent_message_times (username, date) VALUES (%s, NOW())", [username])

        self.database_connection.commit()

    async def handle_admin_comands(self, message):
        if message.content.startswith("!") and message.channel.name == "bottikomennot": # TODO: channel id
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
                await message.channel.send(self.get_settings_string())
            elif message.content.startswith("!autodelete aja-nyt"):
                await message.channel.send("Ok, ajetaan kaikki autodeletoinnit nyt.")
                self.trigger_all_jobs_now()
            elif message.content.startswith("!autodelete lopeta"):
                tokens = message.content.split()
                
                # Check the number of parameters
                if len(tokens) != 3:
                    await message.channel.send("Virhe: Väärä määrä parametreja. Komennolle `!autodelete lopeta` täytyy antaa yksi parametri.")
                    return
                
                await message.channel.send("TODO") # TODO: update database

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
                
                await message.channel.send("TODO") # TODO: update database and start job
            else:
                await message.channel.send("Tuntematon komento: " + message.content.split()[0])
    
    async def process_message(self, message):

        self.add_message_to_db(message.author.name)

        await self.handle_admin_commands(message)

        if message.content.startswith("!roll"):
            expression = message.content[5:].strip()
            try:
                result = konso_dice_roller.markdown_roll_string_from_input(expression, number_of_dice_limit=100, dice_sides_limit=10**6, bonus_absolute_value_limit=10**6)
                await message.channel.send(message.author.display_name + " heitti " + result)
            except Exception as e:
                await message.channel.send(message.author.display_name + " heitti `" + expression + "`. Virhe: " + str(e))

        elif message.content.startswith("!vanharoll"):
            expression = message.content[10:].strip()
            if(len(expression) == 0):
                await message.channel.send("Virhe: anna heitto muodossa 2d6 + 5")
            else:
                result = roll.do_roll(expression)
                await message.channel.send(message.author.display_name + " heitti `" + expression.strip() + "`, tulos: `" + result + "`")
        
