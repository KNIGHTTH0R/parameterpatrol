import logging
import mechanize
import mechanizePatch
import re
import datetime
from BeautifulSoup import BeautifulSoup

###########################################################
# Class: ArchiveFetcher
# Purpose: Fetches chosen archives for a given domain
###########################################################
class ArchiveFetcher:

  def __init__(self):

    #logging
    self.logger = logging.getLogger(__name__)

    #True/False if archives were found/not found
    self.archivesAvailable = None

    #save available archives
    self.archiveYears = list() #save yyyy
    self.archiveUrls = list() #save full date reference yyyymmdd...

    #discovered start and end of online archive years
    self.yearStart = None
    self.yearEnd = None

  
  #lookup dates available for user's chosen year at: https://web.archive.org/web/[yyyy]*/[targetdomain]
  def setOnlineArchiveDates(self, targetDomain, year):
    self.logger.info('Searching the ' + str(year) + 'archives...')
    
    searchURL = 'https://web.archive.org/web/'+str(year)+'*/'+targetDomain
    self.logger.info('searching ' + searchURL)

    #extract links from this page
    mechanizePatch.monkeypatch_mechanize() #TODO: move into main class init method
    br = mechanize.Browser()
    br.set_handle_robots(False) #ignore robots.txt

    try:
      br.open(str(searchURL))

      #Searches https://web.archive.org/web/yyyy*/[targetDomain] page and pulls out all links for days/months
      for link in br.links():
        try:
          if re.search(r'\*', str(link.url)) is None: #ignore links containing an astertix (want specific dates at this point only)
            match = re.search(r'/web/\d{4}', link.url) #only work with urls of format /web/yyyy...
            archiveDate = str(match.group())[5:] #only interested in yyyy portion of url, remove /web/
            if int(archiveDate) == year: #only save archives belonging to user's chosen search year
              self.archiveUrls.append(link.url) #build list of available archive URLs for user's search year
        except:
          pass #silenty ignore irrelevant links 

      self.archiveUrls = list(set(self.archiveUrls)) #create unique list
      self.archiveUrls.sort() #sort list
    
      self.archivesAvailable = True #archive(s) available for selected year

    except (mechanize.HTTPError,mechanize.URLError) as e:
      self.archivesAvailable = False #no archive found for selected year


  #query archive.org for the targetdomain's oldest and newest archive years
  def setOnlineArchiveYearRange(self, targetDomain, URL):

    print 'Searching archive.org for archives belonging to', targetDomain,'...'

    self.URL = URL 
    self.targetDomain = targetDomain   

    try:
      #use mecahanize to fetch the html page showing all years /web/*/targetdomain
      mechanizePatch.monkeypatch_mechanize() #TODO: move into main class init method
      br = mechanize.Browser()
      br.set_handle_robots(False) #ignore robots.txt
      html = br.open(self.URL).read()

      #use BeautifulSoup to parse the html containing the start and end of the archives in the section "<div id="wbMeta">"
      soup = BeautifulSoup(html)
      listedArchives = soup.findAll('div', attrs={"id" : "wbMeta"})
      for line in listedArchives: #need to parse results line by line due to datatype returned
        links = line.findAll('a', href=True)

      #extract 2 links from the links list with the format /web/yyyy
      for link in links:
        link = link.__str__('utf-8') #covert from BeautifulSoup.Tag Resultset to string for searching
        match = re.search(r'/web/\d{4}', link) #expect 2 links to match this pattern (oldest and newest archive)
        if match is not None:
          archiveDate = str(match.group())[5:] #remove /web/ and leave d{8}
          self.archiveYears.append(archiveDate)
          self.archiveYears.sort()

      #convert to archive years once found
      try:
        self.startYear = int(self.archiveYears[0])
        self.endYear = int(self.archiveYears[1])

        self.logger.debug('user provided start year: ' + str(self.startYear))
        self.logger.debug('user provided end year: ' + str(self.endYear))
      except: 
        print 'No archives found. Please try manually searching for available years at: https://web.archive.org/web/*/',targetDomain

    except (mechanize.HTTPError, mechanize.URLError) as e:  #catch any 404s
      print 'No archives found. Please try manually searching for available years at: https://web.archive.org/web/*/',targetDomain



  #fetch all links associated with a URL
  def getArchives(self, URL, yearStart):
    self.URL = URL
    self.tmpList = list()
    self.yearStart = yearStart

    self.logger.debug('looking for ' + self.URL)

    mechanizePatch.monkeypatch_mechanize() #TODO: move into main class init method
    br = mechanize.Browser()
    br.set_handle_robots(False) #ignore robots.txt
    br.open(self.URL)

    self.logger.debug('Searching waybackmachine in year ' + self.yearStart)

    #Searches https://web.archive.org/web/*/[domain] page and pulls out all links for all years
    for link in br.links():
      self.logger.debug('found archive url ' + link.url)
      #filter based on year: 1st 4 digits in string i.e. format of waybackmachine calendar urls are: "/web/yyyy..."
      match = re.search(r'^/web/\d{4}', link.url)
      if match is not None:				
        #remove "/web/" from string so we can search by year
        archivedCalendarYear = str(match.group())[5:]
        #print 'checking url ', link.url, ' it has archived year of ', archivedCalendarYear
        if (archivedCalendarYear == self.yearStart):  
          self.logger.debug('found match: ' + link.url)
          self.tmpList.append(link.url) #build list of archive sites

    #return list of archives URLs
    return self.tmpList


  def extractDateTimeFromURLFormatted(self, url):
    match = re.search(r'/web/\d{14}', url) #datetime is 14 chars long in the url yyyymmddhhmmss
    dateTime = str(match.group())[5:] #datetime starts at the 5th position within our matched text
    dateTime = datetime.datetime.strptime(dateTime,'%Y%m%d%H%M%S')
    return dateTime


  def extractDateTimeFromURL(self, url):
    match = re.search(r'/web/\d{14}', url) #datetime is 14 chars long in the url yyyymmddhhmmss
    dateTime = str(match.group())[5:] #datetime starts at the 5th position within our matched text
    return dateTime

