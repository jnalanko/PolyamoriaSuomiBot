import sys

import discord
import yaml
import logging

import config
from mybot import MyBot

logging.basicConfig(level=logging.INFO)

# Set to remember if the bot is already running, since on_ready may be called
# more than once on reconnects
this = sys.modules[__name__]
this.running = False

yaml_filename = "config_local.yaml"
cfg = yaml.safe_load(open(yaml_filename))
logging.info(f"Config: {config.censor_config(cfg)}")
if cfg.get('DEBUG'):
    logging.warning("Debug mode active - do not run in production!")

# Initialize the client
logging.info("Starting up...")
bot = discord.Bot(intents=discord.Intents(message_content=True, guild_messages=True, guilds=True, messages=True, members=True))
mybot = None

# Define event handlers for the client
# on_ready may be called multiple times in the event of a reconnect,
# hence the running flag
@bot.event
async def on_ready():
    global mybot

    if this.running: return
    else: this.running = True

    print("Client started up.", flush=True)
    mybot = MyBot(cfg["guild_id"], cfg["bot_channel_id"], cfg["midnight_channel_id"], cfg["lukija_role_id"], cfg["osallistuja_role_id"], cfg["db_name"], cfg["db_user"], cfg["db_password"], cfg["admin_user_id"], cfg["activity_ignore_channel_ids"], bot)

    mybot.startup()

@bot.event
async def on_message(message: discord.Message):
    if cfg.get('DEBUG'):
        logging.info(f"on_message {message.content}")
    else:
        logging.info(f"on_message {message.id}")
    if message.guild is None:
        return  # DM?
        
    await mybot.process_message(message)

@bot.event
async def on_member_join(member: discord.Member):
    await mybot.on_member_join(member)

@bot.slash_command(guild_ids=[cfg["guild_id"]], name="midnight-winners", description="Midnight winners")
async def midnight_winners(ctx):
    await mybot.midnight_winners_command(ctx)

#@bot.slash_command(guild_ids=guild_ids, name="threads", description="List of threads")
#async def threads(ctx):
    #await instances[ctx.guild_id].list_threads_command(ctx)
#    pass

@bot.slash_command(guild_ids=[cfg["guild_id"]], name="viestilaskuri", description="Viimeisen 3kk:n viestimäärä DM:llä")
async def message_count(ctx):
    await mybot.message_count_command(ctx)
    pass

bot.run(cfg["token"])
