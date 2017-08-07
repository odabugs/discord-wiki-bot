from DiscordBotClient import DiscordBotClient
from cachetools import TTLCache
import requests
import re

canLinkByTitle = re.compile("^[ \w:'/+]+$")
emptySet = set()
emptyMap = {}
def identity(x, *args):
	return x
def asSet(x, *args):
	return set(x)

def postprocessResults(response, postprocess, fallback):
	asJson = response.json()
	result = None
	try:
		result = asJson["query"]["pages"]
	except:
		return fallback
	return postprocess(result)
def resultMap(response, *args):
	return postprocessResults(response, identity, emptyMap)
def resultIDs(response, *args):
	return postprocessResults(response, asSet, emptySet)

class DiscordWikiBotClient(DiscordBotClient):
	def __init__(self, config):
		super().__init__(config)
		self.addCommandHandler("wiki", self.wikiLookup)
		self.queryCache = TTLCache(
			maxsize=config.resultCacheSize,
			ttl=config.resultTTL,
			missing=self.fetchSearch)
		self.categoryCache = TTLCache(
			maxsize=config.categoryCacheSize,
			ttl=config.categoryTTL,
			missing=self.fetchCategory)

	def fetchResponse(self, params, postprocess=identity, *args):
		response = requests.get(
			self.config.queryURL,
			params,
			timeout=self.config.searchTimeout)
		response.raise_for_status() # throw an exception if respose code is not 200
		return postprocess(response, *args)

	def fetchSearch(self, query):
		#print("Calling fetchSearch for key: " + query)
		params = {
			"action": "query",
			"format": "json",
			"generator": "search",
			"gsrlimit": "max",
			"gsrsearch": query,
		}
		return self.fetchResponse(params, resultMap, emptyMap)

	# return a set containing the page ID # of each page in the category
	def fetchCategory(self, cat):
		#print("Calling fetchCategory for key: " + cat)
		params = {
			"action": "query",
			"format": "json",
			"generator": "categorymembers",
			"prop": "categories",
			"gcmlimit": "max",
			"gcmtitle": cat,
		}
		return self.fetchResponse(params, resultIDs, emptySet)

	def getCategoryReference(self, query):
		splitQuery = query.split(maxsplit=1)
		if len(splitQuery) < 2:
			return None
		categoryKey = splitQuery[0].lower()
		return self.config.aliases.get(categoryKey, None)

	def basicSearch(self, query):
		result = self.queryCache[query]
		if len(result) == 0:
			return None
		return result.popitem()[1]

	def categorySearch(self, category, query):
		# query still contains the category at this point; remove it
		query = query.split(maxsplit=1)[1]
		catResult = self.categoryCache[category["title"]]
		queryResult = self.queryCache[query]
		filtered = self.mapIntersection(queryResult, catResult)
		aliases = category["aliases"]
		if len(filtered) == 0:
			return None
		# search results that contain an alias of the category name
		# in their title are favored above the rest
		for pageID, result in iter(filtered.items()):
			pageTitle = result["title"].lower()
			for alias in aliases:
				if alias in pageTitle: # this is how python finds substrings
					return result
		# failing the above, just pop off an arbitrary result and return it
		return filtered.popitem()[1]

	def asWikiLink(self, result):
		#print(result)
		title = result["title"]
		if canLinkByTitle.match(title):
			return self.config.titleLinkURL + title.replace(" ", "_")
		else:
			return "".join([
				self.config.linkURL,
				str(result["pageid"]),
				" (", result["title"], ")"])

	async def wikiLookup(self, message):
		query = self.partAfterCommand(message)
		if query is None:
			await self.reply(message,
				"Type **!wiki** followed by a name or game + name to search")
			return
		try:
			#print("Starting query: " + query)
			result = None
			category = self.getCategoryReference(query)
			if category is not None:
				#print("Performing category search: " + category["title"])
				result = self.categorySearch(category, query)
			else:
				#print("Performing basic search")
				result = self.basicSearch(query)
			if result is None or len(result) == 0:
				await self.reply(message, str.format(
					"No result found for search query **{}**",
					query))
			else:
				await self.reply(message, self.asWikiLink(result))
		except requests.Timeout:
			await self.reply(message,
				"**ERROR:** Search request took too long to return a response")
		except requests.HTTPError:
			await self.reply(message, str.format(
				"**ERROR:** Search request failed with HTTP status code {}",
				response.status_code))
		except:
			await self.reply(message, 
				"**ERROR:** Search request returned invalid content from the server")
		#print("Finished query: " + query)
