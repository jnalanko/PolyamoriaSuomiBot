# Installing
## Prerequisites
- python (TODO: define exact version)
- mysql and a database dedicated to the bot
  - currently mysql must be running at `localhost` and use the default port
- discord bot account (details below)
## Steps
- clone this repo
- create a venv: `python -m venv venv`
- activate the venv:
  - linux: `source venv/bin/activate`
  - windows: `venv\scripts\activate`
- install requirements: `pip install -r requirements.txt`
- create a Discord bot account: https://discordpy.readthedocs.io/en/stable/discord.html
  - enable `Server Members Intent` and `Message Content Intent`
  - save the token securely
  - invite the bot to your server
    - TODO: what are the exact required permissions?
    - quick test with permissions integer `397552987232` seems to work
- copy `config.yaml` to `config_local.yaml` and set the settings there
- start the bot with `python bot.py`
