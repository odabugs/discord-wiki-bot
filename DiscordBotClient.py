from discord import Client, Game
from datetime import datetime
import time
import re
import asyncio
import tzlocal

commandPrefix = "!"
emptyPair = (None, None)

class DiscordBotClient(Client):
	def __init__(self, config):
		super().__init__()
		self.config = config
		self.commandHandlers = {}
		self.localTimeZone = tzlocal.get_localzone()

	def mapIntersection(self, myMap, mySet):
		result = {}
		intersection = mySet.intersection(myMap)
		for key in intersection:
			result[key] = myMap[key]
		return result

	def log(self, message, *args):
		rawTime = time.time()
		localTime = datetime.fromtimestamp(rawTime, self.localTimeZone)
		timestamp = localTime.strftime(self.config.timestampFormat)
		if len(args) > 0:
			message = message.format(*args)
		print("[", timestamp, "] ", message, sep="")

	def commandRE(self, command):
		pattern = "".join(["^", commandPrefix, command, ".*$"])
		return re.compile(pattern)

	def partAfterCommand(self, message):
		try:
			return message.content.split(maxsplit=1)[1]
		except (TypeError, IndexError):
			return None

	def addCommandHandler(self, key, handler):
		self.commandHandlers[self.commandRE(key)] = handler

	def lookupCommandHandler(self, message):
		if message.content.startswith(commandPrefix):
			for pair in iter(self.commandHandlers.items()):
				if pair[0].match(message.content):
					return pair
		return emptyPair

	# "mentions" the replied-to user if the message isn't in a PM
	@asyncio.coroutine
	def reply(self, message, reply, suppressNotify=False):
		if not suppressNotify and not message.channel.is_private:
			reply = "".join([message.author.mention, ": ", reply])
		yield from self.send_message(message.channel, reply)

	@asyncio.coroutine
	def on_ready(self):
		user = self.user
		self.log("Logged in as {}#{} (ID: {})",
			user.name, user.discriminator, user.id)
		self.log("Press Ctrl-C in this console window to exit.")
		nowPlaying = self.config.nowPlaying
		if len(nowPlaying) > 0:
			asGame = Game(name=nowPlaying)
			yield from self.change_presence(game=asGame)

	@asyncio.coroutine
	def on_message(self, message):
		if message.author == self.user:
			return
		key, handler = self.lookupCommandHandler(message)
		if callable(handler):
			yield from handler(message)
