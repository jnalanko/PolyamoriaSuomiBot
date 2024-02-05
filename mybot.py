from collections import defaultdict

from datetime import datetime, timedelta, timezone

from zoneinfo import ZoneInfo

from mysql.connector.pooling import MySQLConnectionPool

import discord

from database import open_database
import midnight
from nick import update_nickname_cache, get_nick
from send_dm import send_dm

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import konso_dice_roller.konso_dice_roller as konso_dice_roller
import roll


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
                    prev_time = datetime.now(timezone.utc)  - timedelta(minutes=delete_older_than_minutes)

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
    def __init__(self, guild_id, bot_channel_id, midnight_channel_id, ei_osallistuja_role_id, ei_aktiivi_role_id, db_name, db_user, db_password, admin_user_id, api):
        self.guild_id = guild_id
        self.sched = AsyncIOScheduler()
        self.autodelete = AutoDeleteCallBack()
        self.jobs = dict() # channel id -> job
        self.bot_channel_id = bot_channel_id
        self.admin_user_id = admin_user_id
        self.midnight_channel_id = midnight_channel_id
        self.ei_osallistuja_role_id = ei_osallistuja_role_id
        self.ei_aktiivi_role_id = ei_aktiivi_role_id
        self.api = api
        self.connection_pool: MySQLConnectionPool = open_database(db_name, db_user, db_password)
    
    # If no job is yet active, creates a new job
    def set_autodel(self, channel_id, callback_interval_minutes, delete_older_than_minutes): # returns new autodel config

        # Check if autodelete is already active for the channel and if so, update config the values
        with self.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("REPLACE INTO autodelete (channel_id, callback_interval_minutes, delete_older_than_minutes) VALUES (%s, %s, %s)", [channel_id, callback_interval_minutes, delete_older_than_minutes])

            # Create a job (terminates existing job if exists)
            self.create_job(channel_id, callback_interval_minutes, delete_older_than_minutes)
            conn.commit()

    # Updates config and removes the affected job (if exists)
    def remove_autodel_from_channel(self, channel_id):
        with self.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM autodelete WHERE channel_id = %s", [channel_id])

            if channel_id in self.jobs:
                self.jobs[channel_id].remove()
                del self.jobs[channel_id]

            conn.commit()

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
        with self.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
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

        with self.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM autodelete")
            for row in cursor.fetchall():
                channel_id, interval_minutes, delete_older_than_minutes = row
                channel_name = self.api.get_channel(channel_id).name
                lines.append("**#{}**: {:.2f} tunnin välein vähintään {:.2f} päivää vanhat viestit.".format(channel_name, interval_minutes/60, delete_older_than_minutes/(60*24)))
        
        return "\n".join(lines)
        
    def increment_todays_message_count(self, user_id):

        with self.connection_pool.get_connection() as conn:
            cursor = conn.cursor()

            # Create a new counter or increment existing
            cursor.execute("INSERT INTO message_counts (user_id, date, count) VALUES (%s, CURDATE(), 1) ON DUPLICATE KEY UPDATE count = count + 1;", [user_id])

            conn.commit()

    async def handle_bot_channel_message(self, message):
        if message.content.startswith("!"):
            if message.content.startswith("!ohjeet"):
                lines = []
                lines.append("**PolyamoriaSuomiBot**")
                lines.append("")
                lines.append("Komento **!ohjeet** tulostaa tämän käyttöohjeen. Komento **!asetukset** näyttää nykyiset asetukset. Muita komentoja ovat:")
                lines.append("")
                lines.append("**!autodelete** aseta [kanavalinkki] [aikahorisontti päivinä] [kuinka monen tunnin välein poistot tehdään]")
                lines.append("**!autodelete** aja-nyt")
                lines.append("**!autodelete** lopeta [kanavalinkki]")
                lines.append("")
                lines.append("Esimerkiksi jos haluat asettaa kanavan #mielenterveys poistoajaksi 60 päivää siten, että poistot tehdään kerran päivässä, anna kirjoita komentokanavalle komento `!autodelete aseta #mielenterveys 90 24`. Annetuiden numeroiden on oltava kokonaislukuja. Tällä komennolla voi myös muokata olemassaolevia asetuksia kanavalle. Jos haluat myöhemmin ottaa poiston pois päältä, anna komento `!autodelete lopeta mielenterveys`.")
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
    
    def message_datetime_in_helsinki(self, message):
        return message.created_at.astimezone(ZoneInfo("Europe/Helsinki"))
    
    def message_date_in_helsinki(self, message):
        return self.message_datetime_in_helsinki(message).date()

    # Returns the emoji prize, or None if the prize for today has already been won by someone
    # If there was a winner, it's stored in the database.
    def check_midnight_winner(self, message) -> str:
        helsinki_date = self.message_date_in_helsinki(message)
        if message.channel.id == self.midnight_channel_id and midnight.contains_midnight_phrase(message.content):
            # Winner
            prize = midnight.get_prize(message.content, helsinki_date)
            assert(len(prize) == 1) # Single character

            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()

                # Check if there exists a column with the current date
                cursor.execute("SELECT * FROM midnight_winners WHERE date = %s", [helsinki_date])
                if len(cursor.fetchall()) > 0:
                    return # Already have a winner for today

                cursor.execute("INSERT INTO midnight_winners (date, user_id, prize) VALUES (%s, %s, %s)", [helsinki_date, message.author.id, prize])

                conn.commit()
            return prize
        return None
    
    async def message_count_command(self, ctx):
        with self.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(count) FROM message_counts WHERE user_id = %s", [ctx.author.id])
            rows = cursor.fetchall()
            if len(rows) != 1 or len(rows[0]) != 1:
                await ctx.send_response(
                        content="Virhe! Sori, en osannut.",
                        ephemeral=True,
                    )
            else:
                count = int(rows[0][0])
                try:
                    await ctx.send_response(
                            content="Olet lähettänyt tarkastelujakson aikana {} viestiä.".format(count),
                            ephemeral=True,
                        )
                except:
                    await ctx.send_response(
                            content="Yritin lähettää viestien määrän, mutta se ei onnistunut.",
                            ephemeral=True,
                        )

    async def list_threads_command(self, ctx):
        lines = []
        n_threads = 0
        for channel in ctx.guild.channels:
            if not hasattr(channel, "threads"):
                continue
            all_threads = channel.threads
            
            #async for T in channel.archived_threads(limit=None):
            #    all_threads.append(T)
            for thread in all_threads:
                n_threads += 1
                lines.append("<#{}>".format(thread.id))
        
        await ctx.respond("**Threads** ({} total)".format(n_threads))
        for i in range(0, len(lines), 50):
            await ctx.send_followup("\n".join(lines[i:i+50]))
        
    async def midnight_winners_command(self, ctx):
        with self.connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, date, prize FROM midnight_winners")
            winners = cursor.fetchall()

        # Collect total win counts and counts for individual trophies
        total_wins = defaultdict(int) # User id -> total win count
        prizes = defaultdict(lambda : defaultdict(int)) # User id -> dict of (prize -> count)
        distinct_prizes = set()
        for (user_id, date, prize) in winners:
            total_wins[user_id] += 1
            prizes[user_id][prize] += 1
            distinct_prizes.add(prize)

        # List users in decreasing order of total wins
        lines = []
        lines.append("**Midnight Winners**")
        pairs = [(total_wins[user_id], user_id) for user_id in total_wins]
        for i, (wins, user_id) in enumerate(sorted(pairs)[::-1]): # In descending order
            nick = get_nick(user_id, guild=ctx.guild)
            counts = [(trophy, prizes[user_id][trophy]) for trophy in prizes[user_id].keys()] # Pairs (trophy, count)
            lines.append("**{}**. **{}**: {}".format(i+1, nick, midnight.format_trophy_counts(counts)))
        await ctx.respond("\n".join(lines))

    async def process_message(self, message):
        message_time = self.message_datetime_in_helsinki(message)
        if message_time.hour == 0 and message_time.minute == 0:
            prize = self.check_midnight_winner(message)
            if prize != None:
                await message.add_reaction(prize)

        self.increment_todays_message_count(message.author.id)
        update_nickname_cache(message.author, self.guild_id)

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

    async def on_member_join(self, member: discord.Member):
        await member.add_roles(self.api.get_guild(self.guild_id).get_role(self.ei_osallistuja_role_id))
        
