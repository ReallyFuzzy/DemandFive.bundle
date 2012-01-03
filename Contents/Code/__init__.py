import re

TITLE				= "Demand Five"
PLUGIN_PREFIX   	= "/video/fivetv"
ROOT            	= "http://www.channel5.com"
SHOW_URL			= "%s/shows/" % ROOT
EPISODE_URL			= "/episodes/"
A_Z					= "%s/shows/" % ROOT
WATCH_NOW			= "%s/WatchNow.aspx" % ROOT
GENRE               = "%s/shows?genre=" % ROOT
SEARCH				= "%s/search?q=" % ROOT
FEED_LAST_NIGHT		= "%s/Handlers/LastNightRssFeed.ashx" % ROOT
FEED_NEW			= "%s/demand5.atom" % ROOT
FEED_POPULAR		= "%s/Handlers/PopularRssFeed.ashx" % ROOT
FEED_RECOMMENDED	= "%s/Handlers/RecommendedRssFeed.ashx" % ROOT

####################################################################################################
def Start():

	# Add the MainMenu prefix handler
	Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, L(TITLE))
	
	# Set up view groups
	Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
	Plugin.AddViewGroup("Info", viewMode="InfoList", mediaType="items")
	
	# Set the default cache time
	HTTP.CacheTime = 14400
	HTTP.Headers['User-agent'] = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.10) Gecko/20100914 Firefox/3.6.10'
	
	# Set the default MediaContainer attributes
	MediaContainer.title1 = L(TITLE)
	MediaContainer.viewGroup = "List"
	MediaContainer.art = R("art-default.png")

	if Dict["demand5.shows"] is None:
		Dict["demand5.shows"] = {}
	
####################################################################################################
def GetShows(url):

	shows = []
	
	for show in HTML.ElementFromURL(url).xpath("//ul[contains(@class,'shows')]/li"):
	
		if len(show.xpath("a[@class='clearfix']")) == 0:
			continue
		
		showId = getShowId(show.xpath('a')[0].get('href'))
		showTitle = show.xpath('a/em')[0].text.strip()
		shows.append(GetShowInfo(showId, showTitle))
		
	return shows

####################################################################################################
def GetShowInfo(showId, showTitle):

	# Fetch all show pages & store the metadata
	shows = Dict["demand5.shows"]
	
	if showId in shows:
		return shows[showId]
		
	page = HTML.ElementFromURL(SHOW_URL + showId)
	
	title = showTitle
	thumb = page.xpath("//img[@class='main_image']")[0].get('src')
	try:
		summary = unicode(page.xpath("//div[@class='top_show_section']/div[contains(@class,'description')]/p")[0].text.strip())
	except:
		summary = ""
		Log("Error handling summary")
		
	shows[showId] = Show(showTitle,thumb,showId,summary)
			
	Dict["demand5.shows"] = shows
	
	return shows[showId]


####################################################################################################

def GetEpisodes(showId, seasonId=None, seasonName=""):

	episodes = []
	
	url = SHOW_URL + showId + EPISODE_URL
	if (not seasonId is None):
		url = url + "?season=" + seasonId
		
	page = HTML.ElementFromURL(url)
	data = page.xpath("//div[contains(@class,'previous_episodes_container')]//li[@class='clearfix']")
	
	if (seasonId is	None):
		if len(data) == 0:
			data = HTML.ElementFromURL(SHOW_URL + showId).xpath("//li[@class='clearfix']")
		else:
			# Get a list of previous seasons and retrieve data for them.
			seasons = page.xpath("//div[contains(@class,'previous_episodes_container')]/div[@class='group_container']//a")
			for season in seasons:
				seasonId = re.search("season=(\d*)",season.get('href')).group(1)
				episodes.extend(GetEpisodes(showId, seasonId, season.text))
			

	cnt = 0
	
	for result in data:
		if len(result.xpath(".//p[@class='vod_availability']")) == 0:
			continue
		episode = Episode(result,showId)
		if seasonName <> "":
			episode.title = episode.title + ", " + seasonName
			episodes.append(episode)
		else:
			episodes.insert(cnt,episode)
			cnt = cnt + 1
		
	return episodes

####################################################################################################

def MainMenu():
	dir = MediaContainer()
	dir.Append(Function(DirectoryItem(AtoZ, title=L("Programmes A to Z"))))
	#dir.Append(Function(DirectoryItem(Feeds, title=L("Last Night on Five")),feed=FEED_LAST_NIGHT))
	dir.Append(Function(DirectoryItem(Feeds, title=L("New on Demand Five")),feed=FEED_NEW))
	#dir.Append(Function(DirectoryItem(Feeds, title=L("Popular on Demand Five")),feed=FEED_POPULAR))
	#dir.Append(Function(DirectoryItem(Recommended, title=L("Recommended by Demand Five"))))
	dir.Append(Function(DirectoryItem(Genre, title=L("Genres"))))
	dir.Append(Function(SearchDirectoryItem(Search,"Search", L("SearchItem"), L("Search for shows on Demand 5"))))
	return dir

####################################################################################################

def Search(sender,query):

	dir = MediaContainer(title2=L("SEARCH"))	
	page = HTML.ElementFromURL(SEARCH + query)

	for show in page.xpath("//ul[contains(@class,'show_search_results')]/li"):
		
		if len(show.xpath(".//a[@class='demand5']")) == 0:
			continue
			
		try:
			GetShowInfo(
				getShowId(show.xpath(".//h3/a")[0].get('href')),
				show.xpath(".//h3/a")[0].text
			).append(dir,query)
			
		except:
			Log("Error loading show")
			
	return dir

####################################################################################################

def AtoZ(sender):

	dir = MediaContainer(title2=L("A to Z"))
	
	for show in GetShows(A_Z):
		show.append(dir,"A to Z")
			
	return dir

####################################################################################################

def Feeds(sender, feed):

	dir = MediaContainer(title2=L(sender.itemTitle))
	doc = XML.ElementFromURL(feed, cacheTime=0)
	ns =  {
		'dcterms':"http://purl.org/dc/terms/",
		'media':"http://search.yahoo.com/mrss/",
		'at':"http://www.w3.org/2005/Atom",
		'html':'http://www.w3.org/1999/xhtml'
	}

	for item in doc.xpath("//at:entry",namespaces=ns):
	
		title = item.xpath("./at:title", namespaces=ns)[0].text
		url = item.xpath("./at:link[@rel='alternate']", namespaces=ns)[0].get('href')
		summary = item.xpath("./at:content/html:div/html:p", namespaces=ns)[0].text
		thumb = getLargeImage(item.xpath(".//html:img", namespaces=ns)[0].get('src'))
		
		parts = title.split("-")
		title = parts[0]
		subtitle = parts[len(parts) - 1]
		
		# Split into parts and 
		item = WebVideoItem(url, title=title, subtitle = subtitle, summary=summary, thumb=thumb)
		dir.Append(item)
			
	return dir

####################################################################################################

def Genre(sender,genre=""):
	if genre == "":
		dir = MediaContainer(title2=L("Genre"))
		dir.Append(Function(DirectoryItem(Genre, title=L("Entertainment")),genre="entertainment"))
		dir.Append(Function(DirectoryItem(Genre, title=L("Drama")),genre="drama"))
		dir.Append(Function(DirectoryItem(Genre, title=L("Documentary")),genre="documentary"))
		dir.Append(Function(DirectoryItem(Genre, title=L("Soap")),genre="soap"))
		dir.Append(Function(DirectoryItem(Genre, title=L("Milkshake!")),genre="milkshake!"))
	else:
		dir = MediaContainer(title1=L("Genre"),title2=L(genre))

		for show in GetShows(GENRE + genre):
			show.append(dir,title = show.title)
			
	return dir
	

####################################################################################################

def Recommended(sender,genre=""):
	if genre == "":
		dir = MediaContainer(title2=L("Genre"))
		dir.Append(Function(DirectoryItem(Genre, title=L("Entertainment")),genre="entertainment"))
		dir.Append(Function(DirectoryItem(Genre, title=L("Drama")),genre="drama"))
		dir.Append(Function(DirectoryItem(Genre, title=L("Documentary")),genre="documentary"))
		dir.Append(Function(DirectoryItem(Genre, title=L("Soap")),genre="soap"))
		dir.Append(Function(DirectoryItem(Genre, title=L("Milkshake!")),genre="milkshake!"))
	else:
		dir = MediaContainer(title1=L("Genre"),title2=L(genre))

		for show in GetShows(GENRE + genre):
			show.append(dir,title = show.title)
			
	return dir
	

####################################################################################################
def ListEpsForShow(sender,showId,showTitle):

	dir = MediaContainer(title1=showTitle, viewGroup="Info")
	
	eps = GetEpisodes(showId)
	
	for ep in eps:
		ep.append(dir,showTitle = showTitle)

	return dir

####################################################################################################
def getShowId(url):

	showId = re.search( "/shows/([^/]*)" , url)
	return showId.group(1)
	
####################################################################################################
def getEpId(url):

	showId = re.search( "/shows/.*/episodes/(.*)" , url)
	return showId.group(1)
	
####################################################################################################
def getLargeImage(url):

	return url.replace("list_size","large_size")


####################################################################################################

class Episode:
	title = ""
	subtitle = ""
	thumb = ""
	episodeId = ""
	summary = ""
	showId = ""
	duration = 0

	def __init__(self,data,showId):
	
		# Show Title
		self.showId = showId
	
		# Title
		links = data.xpath(".//div[@class='text_inner']/h3/a")
		self.title = links[0].text.strip()
		
		# URL
		self.episodeId = getEpId(links[0].get('href'))

		try:
			thumb = data.xpath(".//span[@class='thumbnail']/img")[0].get("src")
			self.thumb = getLargeImage(thumb)
		except:
			pass

		temp = data.xpath(".//p[@class='description']")
		try:
			self.summary = unicode(temp[0].text.strip())
		except:
			pass
			
		if self.duration > 0:
			self.summary = self.summary + "\n\n" + self.duration + " minutes"

	def getUrl(self):
		return SHOW_URL + self.showId + EPISODE_URL + self.episodeId

	def append(self,dir, showTitle="", detail=0):
		if self.episodeId != "":
			item = WebVideoItem(self.getUrl(), title=self.title, subtitle=showTitle, summary=self.summary, thumb=self.thumb)
			dir.Append(item)


####################################################################################################

class Show:
	title = ""
	thumb = ""
	showId = ""
	summary = ""

	def __init__(self,title,thumb,showId,summary=""):
		self.title = title
		self.thumb = thumb
		self.showId = showId
		self.summary = summary
	
	def getUrl(self):
		return SHOW_URL + self.showId
	
	def append(self,dir,title=""):
		
		dir.Append(Function(DirectoryItem(ListEpsForShow, title=L(self.title), summary=self.summary,thumb=self.thumb),showId=self.showId, showTitle=self.title))
		#urllib.quote()
