import configparser
import re

categoryMatcher = re.compile("^category\..+$")
defaultSearchTimeout = 10 # seconds
defaultTTL = 10 # seconds
defaultCacheSize = 100 # oldest cache entries are expunged past this many
defaultConnectionLimitPerHost = 10 # max simultaneous connections to the same host
defaultTimestampFormat = "%Y-%m-%d %H:%M:%S.%f %Z"

class Config():
	def __init__(self, sourcePath=None):
		self.parser = None
		self.token = ""
		self.baseURL = ""
		self.queryURL = ""
		self.linkURL = ""
		self.titleLinkURL = ""
		self.nowPlaying = ""
		self.searchTimeout = defaultSearchTimeout
		self.resultTTL = defaultTTL
		self.resultCacheSize = defaultCacheSize
		self.categoryTTL = defaultTTL
		self.categoryCacheSize = defaultCacheSize
		self.connectionLimitPerHost = defaultConnectionLimitPerHost
		self.timestampFormat = defaultTimestampFormat
		self.categories = {}
		self.aliases = {}
		self.aliasPrefixes = []
		self.aliasSuffixes = []
		if sourcePath:
			self.load(sourcePath)

	def load(self, sourcePath):
		print("Reading config from \"" + sourcePath + "\"...")
		self.parser = configparser.ConfigParser(
			interpolation=configparser.ExtendedInterpolation())
		p = self.parser
		p.read(sourcePath)

		# handle "discord" section
		section = p["discord"]
		self.token = section.get("token", self.token)
		self.nowPlaying = section.get("nowPlaying", self.nowPlaying)
		
		# handle "wiki" section
		section = p["wiki"]
		self.baseURL = section.get("baseURL", self.baseURL)
		self.queryURL = section.get("queryURL", self.queryURL)
		self.linkURL = section.get("linkURL", self.linkURL)
		self.titleLinkURL = section.get("titleLinkURL", self.titleLinkURL)

		# handle "search" section
		section = p["search"]
		self.searchTimeout = section.getfloat("searchTimeout", self.searchTimeout)
		self.resultTTL = section.getint("ttl", self.resultTTL)
		self.resultCacheSize = section.getint("cacheSize", self.resultCacheSize)
		self.connectionLimitPerHost = section.getint("maxConnections",
			self.connectionLimitPerHost)

		# handle "logging" section
		section = p["logging"]
		self.timetstampFormat = section.get("timestampFormat",
			raw=True, fallback=self.timestampFormat)

		# handle "categoryDefaults" section
		section = p["categoryDefaults"]
		self.aliasPrefixes = section.get("aliasPrefixes", "").split(",")
		self.aliasSuffixes = section.get("aliasSuffixes", "").split(",")
		self.categoryTTL = section.getint("ttl", self.categoryTTL)
		self.categoryCacheSize = section.getint("cacheSize", self.categoryCacheSize)

		# handle individual category sections
		self.loadCategories()
		self.aliases = self.aliasesToCategories()
		print("Finished reading config from \"" + sourcePath + "\"")

	def loadCategories(self):
		p = self.parser
		for category in p:
			if categoryMatcher.match(category):
				catname = category.split(".")[1].strip()
				source = p[category]
				prefixes = source.get("aliasPrefixes", self.aliasPrefixes)
				suffixes = source.get("aliasSuffixes", self.aliasSuffixes)
				if type(prefixes) is str:
					prefixes = prefixes.split(",")
				if type(suffixes) is str:
					suffixes = suffixes.split(",")
				cat = {
					"name": catname,
					"title": source["title"],
					"aliases": self.getAliases(
						source.get("aliases", "").split(","),
						prefixes, suffixes)
				}
				self.categories[catname] = cat

	def getAliases(self, aliases, prefixes, suffixes):
		if len(aliases) == 0:
			return []
		result = []
		if len(prefixes) > 0:
			for alias in aliases:
				result.extend([prefix + alias for prefix in prefixes])
		result.extend(aliases)
		if len(suffixes) > 0:
			toAdd = []
			for alias in result:
				toAdd.extend([alias + suffix for suffix in suffixes])
			result.extend(toAdd)
		return tuple(map(lambda x: x.lower().replace(" ", ""), result))
	
	# if two categories have overlapping aliases then result is arbitrary
	def aliasesToCategories(self):
		result = {}
		for cat in self.categories.values():
			for alias in cat["aliases"]:
				result[alias] = cat
		return result
