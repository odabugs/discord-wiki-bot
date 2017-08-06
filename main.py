# Tested on Python 3.6 (may work on 3.5, won't work on 3.4 or older)
# Required pip modules: discord.py, requests, cachetools
from Config import Config
from DiscordWikiBotClient import DiscordWikiBotClient
import sys

defaultConfigPath = "default.ini"

if __name__ == "__main__":
	config = Config()
	if len(sys.argv) > 1:
		for configFile in sys.argv[1:]:
			config.load(configFile)
	else:
		config.load(defaultConfigPath)
	client = DiscordWikiBotClient(config)
	client.run(config.token)
