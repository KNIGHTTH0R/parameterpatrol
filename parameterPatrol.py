import errno
import getopt
import logging
import os
import shutil
import sys
import threading, Queue
import re
import archiveFetcher
import validator
import calendar
import Queue
import crawler
import results
import linkConsumer
import time
import urlDataExtractor

########################################################
# Class: ParameterPatrol
# Purpose: Main driver class.
# Also stores user defined settings & search settngs
########################################################
class ParameterPatrol():

  def __init__(self):
  
    #configure logger
    self.logLevel = "ERROR" #default log level
    #logging.basicConfig(stream=sys.stderr, level=self.logLevel)
    self.logger = logging.getLogger(__name__)

    self.interactiveMode = False #user will pass command line options or use interactive mode

    #user supplied target domain and search year
    self.targetDomain = None
    self.yearStart = None
    self.searchDate = None  #user's chosen archive (yyyymmddhhmmss)

    #list of user supplied domains to incude as part of the search
    self.includeDomainList = list()

    #user supplied non-archive.org site
    self.siteLocation = None
    self.nonArchiveOrgSearch = False
    self.nonArchiveOrgDomain = ''

    #wayback machine URLs
    self.baseURL = 'https://web.archive.org'
    #note: format of wayback machine searching is: https://archive.org/web/*/[targetDomain]
    self.searchTargetHTTPLink = None #construct later from user supplied domain(s)
    
    #storage lists
    self.archiveList = list() #level 1 : initial search of /web/xxxxxx*/[targetdomain]
    self.subArchiveList = list() #level 2 : when  /web/xxxxxx*/ appears in search results
    self.linksToCrawl = list()
    
    #crawler queues
    self.crawlerQueue = Queue.Queue()
    self.inQueue = Queue.Queue()
    self.pagesQueue = Queue.Queue()	

    self.urlDataExtractor = urlDataExtractor.URLDataExtractor()
    self.resultsDirectory = None
    self.projectDatabase = None 

    archiveType = None  #archive.org presents http & https links, identify to help user selection

  def printUsage(self):
    print
    print 'Arguments for Searching Archive.org'
    print '-----------------------------------'
    print '\t -t or --target= (mandatory): Specify the target domain to search for on archive.org. Note: http:// or https:// scheme values should be supplied.\n' 

    print '\t -i or --includedomain= (optional): Specify a list of additional domains to include in the crawler. If ommited, searches will only  be performed against the target domain. For example, if \"www.example.com\" is the target domain, \"example.com\" or \"dev.example.com\" would not be included unless specified using the \"-i\" option. This option may be a single domain or a comma seperated list (no spaces). Note: a list of domains which have been excluded by the cralwer are logged in a file named \"uncrawled_domains.log\". If you wish to include an ommited domain, re-run the search again, supplying the domain in the \"-i\" argument list. This option should only be used for related domains e.g. sub-domains like dev.example.com. Listing a third party domain such as anotherexample.com will only cause the crawler to crawl the third party site and cause unnecessary delays.\n'


    print 'Arguments for Searching Other Locations'
    print '---------------------------------------'
    print '\t -s or --site= (mandatory): Specify the name of the site to search which is not located on archive.org. This option can be used to generate results of a current site for later comparison against archive.org results or comparison against an older archive of the site from a previous penetration test. Note: http:// or https:// scheme values should be supplied.\n'


    print 'Usage Examples'
    print '--------------'
    print 'parameterpatrol -t http://www.example.com -i example.com,dev.example.com'
    print '\t Search archive.org for the target domain and include any additional domains listed using the -i option. Since no search year has been provided, interactive mode will be started to help choose an archived year.\n'

    print 'paramterpatrol -s http://localhost:8000'
    print 'paramterpatrol -s http://uat.example.com'
    print '\t Search a non-archive.org location and record the results to a database for comparison.'

    sys.exit(0)



  def configure(self):

    #Parse command line arguments
    try:
      opts, args = getopt.getopt(sys.argv[1:], "hvt:i:s:y:e:", ["help", "verbose", "target=", "includedomain=", "year="])

      if not opts:
        self.printUsage()
        sys.exit(0)

    except getopt.GetoptError as e:
      print e
      self.printUsage()
      sys.exit(0)

    for opt, arg in opts:
      if opt in ('-h', '--help'):
        self.printUsage()
        sys.exit(0)
        
      elif opt in ('-v', '--verbose'):
        self.logLevel = 'DEBUG'  #enable verbose logging
        logging.basicConfig(stream=sys.stderr, level=self.logLevel)
        print 'Log level set to verbose.'

      elif opt in ('-t', '--target'):
        self.targetDomain = arg
        
      elif opt in ('-i', '--includedomain'):
        self.includeDomainList = arg.split(',')
        print 'Including the following domain(s) in the search:'
        for domain in self.includeDomainList:
          print '-', domain
        
      elif opt in ('-y', '--year'):
				#sanity check year format to be: yyyy
        if (re.search(r'^\d{4}$', arg)) is not None:
          self.logger.debug('user supplied search year: ' + arg) 
          self.yearStart = arg
        else:
          sys.exit('Error: Incorrect format for start year. Please use: yyyy')

      elif opt in ('-s', '--site'):
        self.siteLocation = arg

      else:
        print "Insufficent command line options provided."
        self.interactiveMode = True

    #User has chosen to search a non-archive.org site
    #################################################
    if self.siteLocation:
      self.nonArchiveOrgSearch = True
      if self.siteLocation is not None:
        self.nonArchiveOrgDomain = extractProtocolDomainFromURL(self.siteLocation)
        self.logger.debug('use provided base url of: ' + self.nonArchiveOrgDomain)

    #User has chosen to search archive.org
    ######################################
    else:
      #Required argument (must have a target domain to search for)
      if not self.targetDomain:
        print "A target domain must be supplied e.g. python parameterPatrol.py -t www.example.com"
        sys.exit(0)

      if not self.yearStart:
        print "No archive date provided for searching. Performing automatic lookup ..."
        self.interactiveMode = True
        

    if not self.siteLocation:
      #configure waybackmachine search URLs
      self.searchTargetHTTPLink = self.baseURL + '/web/*/' + self.targetDomain
      self.logger.debug('searchTargetHTTPLink set to: ' + self.searchTargetHTTPLink)

  
  def printBanner(self):
    print
    print ' =============================================================== '
    print '| ParamterPatrol v0.1                                           |'
    print '| by poshea                                                     |'
    print '| archive.org is a great resource, please consider donating at: |'
    print '| https://archive.org/donate/                                   |'
    print ' =============================================================== '


#################################################
# Function: Main
# Purpoe: setup and run parameterPatrol class
#################################################
def main():

  pp = ParameterPatrol()
  pp.printBanner()
  pp.configure()            #check if sufficent command lines options passed
  dataCheck = validator.Validator() #functions for performing basic data validation

  #configure the archiveFetcher with user's configuration settings
  archive = archiveFetcher.ArchiveFetcher()

  #archive lookup related variables
  archiveID = None
  index = None

  #Queues to be used when processing parameters
  pagesQueue = Queue.Queue()

  #results handling object for fetching parameters
  res = results.Results(pp.targetDomain)


  #User has chosen to search a non-archive.org site
  #################################################

  #search link provided in the -s paramter only, record results for later comparison and exit
  if pp.nonArchiveOrgSearch: 

    pp.targetDomain = extractDomainFromURL(pp.siteLocation)

    #configure crawler
    crwlr = crawler.Crawler(None, None, pp.targetDomain, pp.includeDomainList, pp.nonArchiveOrgDomain)
    crwlr.crawl(pp.siteLocation)


    #create a queue from the saved links
    for link in crwlr.savedLinks:
      pp.pagesQueue.put(link)

    #use timestamp as database name
    timestamp = time.strftime('%Y%m%d%H%M%S')

    pp.projectDatabase =  timestamp + '.db'

    #open database connection
    res.openDatabase(makeFileSystemFriendly(pp.siteLocation), pp.projectDatabase) 

    #Extract the forms and their parameters from the saved links in the pagesQueue
    consumerThread = linkConsumer.LinkConsumer(pp.pagesQueue, pp.projectDatabase, res)
    consumerThread.daemon = True
    consumerThread.start()
    pp.pagesQueue.join()

    #*continue: save regular site parameters
    #*here: not all params are being saved...
    
    #write results from archive.org to database
    res.saveParameters()

    #close database
    res.closeDatabase()

    #create unique list of ignored domains
    crwlr.foundDomainsList = list(set(crwlr.foundDomainsList))

    #Exit
    sys.exit(0)

  #User has chosen to search archive.org
  ######################################
  #if no args passed / missing command line options. perform automatic search
  if pp.interactiveMode:
    archive.setOnlineArchiveYearRange(pp.targetDomain, pp.searchTargetHTTPLink)
    if len(archive.archiveYears) == 2:
      print 'Found archives on archive.org between:', archive.archiveYears[0], 'and', archive.archiveYears[1]
    else:
      print 'Error: could not automatically discover archives. Please try manually searching for available dates at: https://web.archive.org/web/*/', pp.targetDomain, 'and resubmitting your search query with the -y parameter'

  #user selected year
  year = raw_input('Choose a year to search in this range (yyyy): ')

  #convert user input to int
  try:
    year = int(year)
    #setup archive object for this search year
    archive.startYear = year
    archive.endYear = year
  except:
    print 'Error: Please enter a valid year (yyyy)'
    sys.exit(0)

  #perform basic data validation checks on user supplied year (yyyy)
  if((not dataCheck.isEmpty(year)) and dataCheck.isInteger(year) and dataCheck.isCorrectLength(year, 4) and dataCheck.inRange(year, archive.startYear, archive.endYear)):
    archive.setOnlineArchiveDates(pp.targetDomain, year)  #lookup archives within the user's search year

    #only proceed if archives are available
    if archive.archivesAvailable is True:
      print '\nThe following archive dates are available:'
      index = 1
      for url in archive.archiveUrls:
        if 'http://' in url:
          archiveTypeString = '(http)'
        elif 'https://' in url:
          archiveTypeString = '(https)'
        print index, ':', archive.extractDateTimeFromURLFormatted(url), archiveTypeString
        index += 1

      #user selected date
      archiveID = raw_input('Select an archive number (n): ')

      #convert user input to int
      try:
        archiveID = int(archiveID)
      except:
        print 'Error: Please enter an archive number (n)'
        sys.exit(0)

      #perform basic data validation checks on user supplied arhcive number (n)
      if((not dataCheck.isEmpty(archiveID)) and dataCheck.isInteger(archiveID)  and dataCheck.inRange(archiveID, 1, index-1)):
        url = archive.archiveUrls[int(archiveID)-1]

        # save the user's selected choice of HTTP or HTTPS selected archive
        if 'http://' in url:
          pp.archiveType = 'http://'
        elif 'https://' in url:
          pp.archiveType = 'https://'
        #save the chosen archive date without formatting
        pp.searchDate = archive.extractDateTimeFromURL(url)
        #set the HTTP or HTTPS component of the user's chosen archive link
        pp.targetDomain = updateURLScheme(pp.targetDomain, pp.archiveType) 

        #configure crawler
        crwlr = crawler.Crawler(pp.baseURL, pp.searchDate, pp.targetDomain, pp.includeDomainList, pp.nonArchiveOrgDomain)

        #put user's chosen arcive URL on the queue
        fqurl = pp.baseURL + url #full qualified URL
        sys.stdout.write('%s' %('Crawling your chosen archive. Please be patient as this is a very slow process dependent on response times from archive.org\n'))
        sys.stdout.flush()

        pp.logger.info('About to crawl: ' + fqurl)

        crwlr.crawlArchiveOrg(fqurl) 

        #create a queue from the saved links
        if crwlr.savedLinks:
          for link in crwlr.savedLinks:  #check we have results first
            pp.logger.debug('2 . adding link to queue: ' + link)
            pp.pagesQueue.put(link)
        else:
          print 'Uh oh: No links found. Please check chosen archive exists on archive.org and/or network connection is up. Try again by selecting another archive date.'

        #open database connection
        pp.projectDatabase =  pp.searchDate + '.db'
        
        res.openDatabase(makeFileSystemFriendly(pp.targetDomain), pp.projectDatabase) 

        #Extract the forms and their parameters from the saved links in the pagesQueue
        consumerThread = linkConsumer.LinkConsumer(pp.pagesQueue, pp.projectDatabase, res)
        consumerThread.daemon = True
        consumerThread.start()
        pp.pagesQueue.join()

        #write results from archive.org to database
        res.saveParameters()

        #close database
        res.closeDatabase()

        #print list of ignored domains
        if crwlr.foundDomainsList: #check we have ignored domains to report first
          print 'The following domains were ignored during searching (use the -i argument to include):'
          ignoredDomains = list()
          for domain in crwlr.foundDomainsList:
            ignoredDomains.append(extractDomainFromURL(domain)) #extract domain portion from URL 
          ignoredDomains = list(set(ignoredDomains))  #create unique list of domains
          for domain in ignoredDomains: #print ignored domains
            print ' ', domain
      
      else:
        print 'Error: Please enter a valid archive number between', 1, 'and', index-1

    else:
      print 'No archives were found for selected year. Please try another year.'
      sys.exit(0)


#Extract the domain from a standard url i.e. [domain.com] from domain.com/dir/...
def extractDomainFromURL(url):

  #remove anything after ? if it exists
  beforeKeyword, keyword, afterKeyword = url.partition('?')

  #domain is before 1st trailing / if it exists
  beforeKeyword, keyword, afterKeyword = beforeKeyword.partition('/')

  return beforeKeyword



#Extract the protocol and domain from a standard url i.e. [http(s)://domain.com] from http(s)://domain.com/dir/...
def extractProtocolDomainFromURL(url):
  #sanity check on url format
  if (url.startswith('http')) and ('://' in url):

    #remove anything after ? if it exists
    beforeKeyword, keyword, afterKeyword = url.partition('?')

    #remove any trailing / if exists
    beforeKeyword.rstrip('/')

    return beforeKeyword

  else:
    #url not fully formed, no protocol & domain can be extracted
    return None

 
def makeFileSystemFriendly(fileName):
  return str(fileName).replace('://', '-')


#update url to contain HTTP or HTTPS based on user's archive selection
def updateURLScheme(url, archiveType):

  if 'https://' in url:
    url = url.rsplit('https://', 1)[-1]       
  elif 'http://' in url:
    url = url.rsplit('http://', 1)[-1] 

  url = archiveType + url

  return url


if __name__ == '__main__':
  main()


