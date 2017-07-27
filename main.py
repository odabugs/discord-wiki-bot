# Requires Python 3.5 or newer with "discord" and "requests" installed via pip
import discord
import requests
import configparser
import re

commandPrefix = "!"
wikiAPIPath = "http://www.dreamcancel.com/wiki/api.php"
searchTimeout = 15 # seconds
nowPlaying = discord.Game(name="type !wiki")

def commandRE(command):
	pattern = "".join(["^", commandPrefix, command, ".*$"])
	return re.compile(pattern)

def partAfterCommand(message):
	try:
		return message.content.split(maxsplit=1)[1]
	except (TypeError, IndexError):
		return None

def wikiSearchParams(query):
	params = {
		"action": "query",
		"format": "json",
		"prop": "info",
		"inprop": "url",
		#"generator": "search",
		#"gsrsearch": query,
		"list": "search",
		"srsearch": query,
	}
	return params

def wikiSearch(query):
	params = wikiSearchParams(query)
	response = requests.get(wikiAPIPath, params, timeout=searchTimeout)
	response.raise_for_status() # throw an exception if respose code is not 200
	return response

def resultFromSearch(body):
	if body is None or type(body) is not dict:
		return None
	pages = body["query"]["pages"]
	key, result = pages.popitem()
	return result["fullurl"]

class MyClient(discord.Client):
	def __init__(self):
		super().__init__()
		self.commandHandlers = {
			commandRE("wiki"): self.wikiLookup
		}

	async def say(self, channel, content):
		await self.send_message(channel, content);

	# "mentions" the replied-to user if the message isn't in a PM
	async def reply(self, message, reply):
		#print(reply)
		if not message.channel.is_private:
			reply = "".join([message.author.mention, ": ", reply])
		await self.say(message.channel, reply)

	async def wikiLookup(self, message):
		key = partAfterCommand(message)
		if key is None:
			await self.reply(message,
				"Type **!wiki** followed by a name to search")
			return
		try:
			#print("requesting " + key + "...")
			response = wikiSearch(key)
			asJson = response.json()
			result = resultFromSearch(asJson)
			if result is None:
				await self.reply(message, str.format(
					"No result found for search query **{}**",
					key))
			else:
				await self.reply(message, result)
		except (ValueError, KeyError):
			await self.reply(message, 
				"**ERROR:** Search request returned invalid content from the server")
		except requests.Timeout:
			await self.reply(message,
				"**ERROR:** Search request took too long to return a response")
		except requests.HTTPError:
			await self.reply(message, str.format(
				"**ERROR:** Search request failed with HTTP status code {}",
				response.status_code))

	def lookupCommandHandler(self, message):
		if message.content.startswith(commandPrefix):
			for pair in iter(self.commandHandlers.items()):
				if pair[0].match(message.content):
					return pair
		return (None, None)

	async def on_ready(self):
		user = client.user
		print(str.format("Logged in as {}#{} (ID: {})",
			user.name, user.discriminator, user.id))
		print("Press Ctrl-C in this console window to exit")
		await self.change_presence(game=nowPlaying)

	async def on_message(self, message):
		if message.author == client.user:
			return
		key, handler = self.lookupCommandHandler(message)
		#print(key, handler)
		if handler is not None:
			await handler(message) # "self" is passed implicitly here

client = MyClient()
client.run("token goes here")
