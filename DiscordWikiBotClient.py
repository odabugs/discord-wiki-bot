from DiscordBotClient import DiscordBotClient
from cachetools import TTLCache
from concurrent.futures import FIRST_EXCEPTION
import aiohttp
import asyncio
import time
import re

canLinkByTitle = re.compile("^[ \w:'/+]+$")
emptySet = set()
emptyMap = {}
def identity(x, *args):
	return x
def asSet(x, *args):
	return set(x)

@asyncio.coroutine
def postprocessResults(response, postprocess, fallback):
	asJson = yield from response.json()
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
		self.connector = aiohttp.TCPConnector(
			limit_per_host=config.connectionLimitPerHost)
		self.session = aiohttp.ClientSession(
			connector=self.connector,
			read_timeout=config.searchTimeout,
			raise_for_status=True)
		self.queryCache = TTLCache(
			maxsize=config.resultCacheSize,
			ttl=config.resultTTL)
		self.categoryCache = TTLCache(
			maxsize=config.categoryCacheSize,
			ttl=config.categoryTTL)

	@asyncio.coroutine
	def fetchResponse(self, params, postprocess=identity, *args):
		response = None
		try:
			response = yield from self.session.request("GET",
				self.config.queryURL,
				params=params,
				timeout=self.config.searchTimeout)
		except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
			raise
		result = yield from postprocess(response, *args)
		return result

	@asyncio.coroutine
	def fetchSearch(self, query):
		#print("Calling fetchSearch for key: " + query)
		params = {
			"action": "query",
			"format": "json",
			"generator": "search",
			"gsrlimit": "max",
			"gsrsearch": query,
		}
		result = yield from self.fetchResponse(params, resultMap, emptyMap)
		self.queryCache[query] = result
		#print("Completed fetchSearch for key: " + query)

	# return a set containing the page ID # of each page in the category
	@asyncio.coroutine
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
		result = yield from self.fetchResponse(params, resultIDs, emptySet)
		self.categoryCache[cat] = result
		#print("Completed fetchCategory for key: " + cat)

	def getCategoryReference(self, query):
		splitQuery = query.split(maxsplit=1)
		if len(splitQuery) < 2:
			return None
		categoryKey = splitQuery[0].lower()
		return self.config.aliases.get(categoryKey, None)

	@asyncio.coroutine
	def basicSearch(self, query):
		if query not in self.queryCache:
			yield from self.fetchSearch(query)
		result = self.queryCache[query]
		if len(result) == 0:
			return None
		return next(iter(result.items()))[1]

	@asyncio.coroutine
	def categorySearch(self, category, query):
		# query still contains the category at this point; remove it
		query = query.split(maxsplit=1)[1]
		catTitle = category["title"]
		queryInCache, catInCache = (query in self.queryCache), (catTitle in self.categoryCache)
		if not (queryInCache and catInCache):
			tasks = []
			if not queryInCache:
				tasks.append(asyncio.ensure_future(self.fetchSearch(query)))
			if not catInCache:
				tasks.append(asyncio.ensure_future(self.fetchCategory(catTitle)))
			done, pending = yield from asyncio.wait(tasks,
				timeout=self.config.searchTimeout,
				return_when=FIRST_EXCEPTION)
			if len(pending) > 0:
				raise asyncio.TimeoutError
		queryInCache, catInCache = (query in self.queryCache), (catTitle in self.categoryCache)
		assert (queryInCache and catInCache)
		queryResult = self.queryCache[query]
		catResult = self.categoryCache[catTitle]
		filtered = self.mapIntersection(queryResult, catResult)
		aliases = category["aliases"]
		if len(filtered) == 0:
			return None
		# search results that contain an alias of the category name
		# in their title are favored above the rest
		for pageID, result in iter(filtered.items()):
			pageTitle = result["title"].lower()
			for alias in aliases:
				if alias in pageTitle:
					return result
		# failing the above, just pop off an arbitrary result and return it
		return next(iter(filtered.items()))[1]

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

	@asyncio.coroutine
	def wikiLookup(self, message):
		query = self.partAfterCommand(message)
		startTime = time.time()
		if query is None:
			yield from self.reply(message,
				"Type **!wiki** followed by a name or game + name to search")
			return
		try:
			print("Starting query: " + query)
			result = None
			category = self.getCategoryReference(query)
			if category is not None:
				#print("Performing category search: " + category["title"])
				result = yield from self.categorySearch(category, query)
			else:
				#print("Performing basic search")
				result = yield from self.basicSearch(query)
			if result is None or len(result) == 0:
				yield from self.reply(message, str.format(
					"No result found for search query **{}**",
					query))
			else:
				yield from self.reply(message, self.asWikiLink(result))
		except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
			yield from self.reply(message,
				"**ERROR:** Search request took too long to return a response")
		except aiohttp.ClientResponseError:
			yield from self.reply(message, str.format(
				"**ERROR:** Search request failed with HTTP status code {}",
				response.status))
		except:
			yield from self.reply(message,
				"**ERROR:** Search request returned invalid content from the server")
		print("Finished query in {:0.2f} seconds: {}".format(time.time() - startTime, query))
