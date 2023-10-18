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
    
    create_message_counts_table = """
    CREATE TABLE IF NOT EXISTS message_counts (
        username VARCHAR(255),
        date DATE,
        count INT,
        PRIMARY KEY (username, date)
    )
    """

    cursor.execute(create_message_counts_table)

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
    async def run(self, api, delete_older_than_minutes, channel_id, bot_channel_id, guild_id, admin_user_id):

        guild = api.get_guild(guild_id)
        bot_channel = api.get_channel(bot_channel_id)

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
                    await bot_channel.send("Poistin kanavalta **#{}** viestit ennen ajanhetkeä {} UTC (yhteensä {} viestiä)".format(channel.name, prev_time.strftime("%Y-%m-%d %H:%M:%S"), n_deleted))

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
                        await bot_channel.send("Poistin ketjusta **#{}** viestit ennen ajanhetkeä {} UTC (yhteensä {} viestiä)".format(thread.name, prev_time.strftime("%Y-%m-%d %H:%M:%S"), n_deleted))

        except Exception as e:
            # Send the error message to the admin user as a DM
            await send_dm(api, admin_user_id, "Error deleting from channel {}: {}".format(channel, str(e)))

        if not channel_found:
            # Send the error message to the admin user as a DM
            await send_dm(api, admin_user_id, "Error: could not find channel: " + str(channel_id))


# An object of this class manages the bot for *one* server.
class MyBot:

    # api is of type discord.Client
    def __init__(self, guild_id, bot_channel_id, db_name, db_user, db_password, admin_user_id, api):
        self.guild_id = guild_id
        self.sched = AsyncIOScheduler()
        self.autodelete = AutoDeleteCallBack()
        self.jobs = dict() # channel id -> job
        self.bot_channel_id = bot_channel_id
        self.admin_user_id = admin_user_id
        self.guild_id = guild_id
        self.api = api
        self.database_connection = open_database(db_name, db_user, db_password)
        self.number_of_message_times_to_remember = 5 # Todo: to config
        
    # If no job is yet active, creates a new job
    def set_autodel(self, channel_id, callback_interval_minutes, delete_older_than_minutes): # returns new autodel config

        # Check if autodelete is already active for the channel and if so, update config the values

        cursor = self.database_connection.cursor()
        cursor.execute("REPLACE INTO autodelete (channel_id, callback_interval_minutes, delete_older_than_minutes) VALUES (%s, %s, %s)", [channel_id, callback_interval_minutes, delete_older_than_minutes])
        
        # Create a job (terminates existing job if exists)
        self.create_job(channel_id, callback_interval_minutes, delete_older_than_minutes)

    # Updates config and removes the affected job (if exists)
    def remove_autodel_from_channel(self, channel_id):
        cursor = self.database_connection.cursor()
        cursor.execute("DELETE FROM autodelete WHERE channel_id = %s", [channel_id])

        if channel_id in self.jobs: 
            self.jobs[channel_id].remove()
            del self.jobs[channel_id]

        self.database_connection.commit()

    # Does not update config
    def create_job(self, channel_id, callback_interval_minutes, delete_older_than_minutes):
        if channel_id in self.jobs:
            self.jobs[channel_id].remove() # Terminate existing job

        self.jobs[channel_id] = self.sched.add_job(self.autodelete.run, 'interval', (self.api, delete_older_than_minutes, channel_id, self.bot_channel_id, self.guild_id, self.admin_user_id), minutes=callback_interval_minutes)

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

        cursor = self.database_connection.cursor()
        cursor.execute("SELECT * FROM autodelete")
        for row in cursor.fetchall():
            channel_id, interval_minutes, delete_older_than_minutes = row
            channel_name = self.api.get_channel(channel_id).name
            lines.append("**#{}**: {:.2f} tunnin välein vähintään {:.2f} päivää vanhat viestit.".format(channel_name, interval_minutes/60, delete_older_than_minutes/(60*24)))
        
        return "\n".join(lines)
        
    def increment_todays_message_count(self, username):

        cursor = self.database_connection.cursor()

        # Create a new counter or increment existing
        cursor.execute("INSERT INTO message_counts (username, date, count) VALUES (%s, CURDATE(), 1) ON DUPLICATE KEY UPDATE count = count + 1;", [username])

        self.database_connection.commit()

    async def handle_bot_channel_message(self, message):
        if message.content.startswith("!"):
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
                print("Calling message")
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

                if len(message.channel_mentions) != 1:
                    await message.channel.send("Virhe: kanavalinkki puuttuu tai yli 1 kanavalinkki")
                    return                                

                self.remove_autodel_from_channel(message.channel_mentions[0].id)
                await message.channel.send("Ok, poistin kanavan {} autodeletointiasetukset.".format(message.channel_mentions[0].name))
            
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
                    await message.channel.send("Virhe: Vääränlaiset parametrit. Komennolle `!autodelete aseta` täytyy antaa kanavalinkki ja kaksi positiivista kokonaislukua.")
                    return

                if len(message.channel_mentions) != 1:
                    await message.channel.send("Virhe: kanavalinkki puuttuu tai yli 1 kanavalinkki")
                    return
                
                self.set_autodel(message.channel_mentions[0].id, interval_hours*60, time_horizon_days*24*60)
                await message.channel.send("Ok, asetin kanavan {} poistamaan vähintään {} päivää vanhat viestit {} tunnin välein.".format(channel_name, time_horizon_days, interval_hours))
                
            else:
                await message.channel.send("Tuntematon komento: " + message.content.split()[0])
    
    async def process_message(self, message):

        self.increment_todays_message_count(message.author.name)

        if message.channel.id == self.bot_channel_id:
            await self.handle_bot_channel_message(message)

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
        
