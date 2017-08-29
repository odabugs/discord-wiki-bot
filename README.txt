A basic wiki lookup bot for Discord.
https://github.com/odabugs/discord-wiki-bot

Requirements:
- Python 3.4.2 or newer
- Required pip modules: discord.py aiohttp cachetools tzlocal
- Optional pip modules (for improved performance): cchardet aiodns

First-time setup:
1) Download or clone this repository to any location on your PC.
2) Follow this guide to set up a bot account for your Discord channel:
   https://github.com/Just-Some-Bots/MusicBot/wiki/FAQ
3) Edit the "token" line in default.ini with the appropriate OAuth token,
   taken from the "My Apps" Discord developer page.
4) Edit the "baseURL" line in default.ini with the URL of your wiki's
   home page (minus the "index.php" part and trailing slash).

To start the bot, run the following command:
   python main.py
   (Linux users may have to explicitly use "python3" instead;
   in all cases, check your PATH environment variable and Python 3's
   installation path if you have both Python 2 and Python 3 installed)
NOTE: The config file to load can also be explicitly specified, like this:
   python main.py myconfig.ini
   If no config file is specified, default.ini is used.

Once the bot is running, users can type "!wiki name" to search for something
by name, or "!wiki category name" to restrict their search to a single
category.  The shorthand aliases that correspond to a category are specified
in the configuration file, and only the categories specified there may be used.
Any unrecognized category alias is treated simply as part of the search string.
