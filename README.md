# Installing
## Prerequisites
- Python 3.9
- MariaDB 10.6 running at localhost at the default port
- Discord bot account
## Steps
### Bot setup
- create a Discord bot account: https://discordpy.readthedocs.io/en/stable/discord.html
  - enable `Server Members Intent` and `Message Content Intent`
  - save the token securely
  - invite the bot to your server
    - TODO: what are the exact required permissions?
    - quick test with permissions integer `397552987232` seems to work
### Local repository setup
- clone this repo
- copy `config.yaml` to `config_local.yaml` 
- change local config variables *db_name*, *db_password* and *db_user* to your liking, each referred to later with the same parameter name
- change local config variable for *token* from what you got from Bot setup above
### MariaDB setup
- install MariaDB, use default port etc. and start server (Windows installer starts it for you)
- login as root user as per install credentials
  - login `.\mariadb -u root -p` (.\ for Windows PowerShell)
  - *enter password*
  - should now see in prompt: "MariaDB [(none)]".
- create database and user for bot
  - `CREATE DATABASE db_name;`
  - get user password hash *pw_hash* `SELECT PASSWORD('db_password');`
  - create user with password `CREATE USER db_user IDENTIFIED BY PASSWORD 'pw_hash';`
  - grant privileges to database `GRANT ALL PRIVILEGES ON db_name.* TO db_user;`
### Python environment setup
- create a venv: `python -m venv venv`
- activate the venv:
  - linux: `source venv/bin/activate`
  - windows: `venv\scripts\activate`
- install requirements: `pip install -r requirements.txt`
### Run bot
- start the bot with `python bot.py`
