import logging
import mechanize
import mechanizePatch
import re
import Queue
import validator
import sys
import datetime
import urlDataExtractor
from collections import defaultdict

class Crawler:

  def __init__(self, baseURL, searchDate, targetDomain, includeDomainList, nonArchiveOrgDomain):

    #logging
    self.logger = logging.getLogger(__name__)

    #user provided options
    self.baseURL = baseURL #archive.org's base URL (http(s)://web.archive.org)
    self.searchDate = searchDate #user's chosen archive date yyyymmddhhmmss
    self.targetDomain = targetDomain
    self.includeDomainList = includeDomainList
    self.nonArchiveOrgDomain = nonArchiveOrgDomain

    #record any ignored domains so user can refine search if required
    self.foundDomainsList = list()

    #tracking crawled links
    self.crawledList = list() #links already crawled
    self.savedLinks = list() #save all of the crawled links for later processing

    #init other vars
    self.asterixInURL = None
    
    #functions for performing basic data validation
    self.dataCheck = validator.Validator()

    #searching archive.org can be very slow, let user know program is still working using basic progress bar
    self.progressCounter = 1

    #functions for extracting data from URLs
    self.urlDataExtractor = urlDataExtractor.URLDataExtractor()
 
  
  ###############################################################################################################
  # method: removePreviousSavedLink
  # purpose: search the saveLinks list & remove all other previously saved urls matching this newLinkFingerprint
  ###############################################################################################################
  def removePreviousSavedLink(self, newLinkFingerprint):
    for link in self.savedLinks:
      linkFingerprint =  self.urlDataExtractor.extractURLFingerprint(link)
      if newLinkFingerprint == linkFingerprint:
        self.savedLinks.remove(link)
    return



  ################################################################################
  # method: checkIfPageNameInSavedList
  # purpose: check if the pagename from the URL is already in the savedLinks list
  ################################################################################
  def checkIfPageNameInSavedList(self, link):
    linkFingerprint = self.urlDataExtractor.extractURLFingerprint(link)

    for savedLink in self.savedLinks:
      savedPageFingerprint = self.urlDataExtractor.extractURLFingerprint(savedLink)
      self.logger.debug('linkFingerprint = ' + linkFingerprint + ' savedPageFingerprint = ' + savedPageFingerprint)
      if linkFingerprint == savedPageFingerprint:
        return True
      else:
        pass #keep searching
    return False #no matches found



  ###############################################################################
  # method : crawlArchiveOrg
  # purpose: crawl a given archive.org URL until no more new links can be found;
  #          only crawl unique page name per user chosen archive date
  # note: a generic crawl method could not be used due to archive.org url formats
  ###############################################################################
  def crawlArchiveOrg(self, url):  
    self.logger.debug('crawlArchiveOrg(): ' + url)

    newLinks = list() #save a list of new links to crawl as they are discovered

    #check URL for asterix
    if self.dataCheck.hasAsterix(url):
      self.asterixInURL = True
    else:
      self.asterixInURL = False

    #make sure URL is fully formed
    url = self.setFullyQualifiedURL(url, self.baseURL) 

    #ignore URLs with asterix (these are belonging to other archives non relevant here)
    if self.asterixInURL:
      pass
    else:
      #Only crawl URLs within the user's chosen date
      match = re.search(r'^https://web.archive.org/web/\d{14}', url)  #check archive date in url yyyyddmmddhhss
      if match is not None:
        urlDate = str(match.group())[28:]
   
        if(urlDate == self.searchDate):
          newLinks = self.getLinksArchiveOrg(url, self.progressCounter)  #crawl this page for other links
          self.progressCounter += 1

        #iterate over newly found links to find more
        if newLinks: #check if not empty first
          # create a dictionary for the savedLinks.
          # want to track when we have found an exact match to the user's chosenArchiveDate
          # otherwise, we have to keep search until oldest match is found
          savedLinksBestMatch = defaultdict(dict)

          for link in newLinks:              
              #make sure URL is fully formed
              link = self.setFullyQualifiedURL(link, self.baseURL)

              #check link has not already been crawled
              if link not in self.crawledList:

                linkFingerprint = self.urlDataExtractor.extractURLFingerprint(link)

                if self.checkIfPageNameInSavedList(link):
                  if not savedLinksBestMatch[linkFingerprint]: #if we haven't found an exact match
                    self.saveMostRelevantLink(link, savedLinksBestMatch)  #check if we can find a closer match to user's selected date
                else: 
                  self.savedLinks.append(link) #if pageName not in savedList, add it (can be replaced later by a better one if it comes along)
                  #cases where the 1st instance of a link is the best match
                  newArchiveDate = self.urlDataExtractor.extractArchiveDateFromURL(link)
                  newArchiveDate = datetime.datetime.strptime(newArchiveDate, '%Y%m%d%H%M%S')
                  usersChosenDate = datetime.datetime.strptime(self.searchDate, '%Y%m%d%H%M%S')

                  if usersChosenDate == newArchiveDate:
                    savedLinksBestMatch.update({linkFingerprint:True})
                  else:
                    savedLinksBestMatch.update({linkFingerprint:False})
       

                self.crawlArchiveOrg(link) #search this link for more links

      #create a unique list of all saved crawled URLs
      self.savedLinks = list(set(self.savedLinks))


  #######################################################################################################
  # method: saveMostRelevantLink
  # purpose: before saving a link, make sure we are saving the most relevant link for the 
  # user's selected archive date by checking incoming newLink against savedLink list to see 
  # if it's a better match
  # 
  # using 3 parameters here:
  #   1. newLink's date
  #   2. savedLink's date
  #   3. user chosen's date
  #
  # Then, compare newLink's date to user's chosen date
  # Update savedLink list based on result (replace or keep)
  #
  # Note: introducting a dictionary here to keep track of best matches 
  # Needed a new data struct as savedLinks must be a full archive.org URL
  # couldn't use savedLinks as searching needs to be independent of archiveYear in archive.org URL
  # could have created a 2d dictionary to hold ArchiveOrgURL URLFingerprint & best matched boolean flag, 
  # just haven't integrated it back into non-archive.org code (TODO in a cleanup)
  #######################################################################################################
  def saveMostRelevantLink(self, newLink, savedLinksBestMatch):

    newLinkFingerprint = self.urlDataExtractor.extractURLFingerprint(newLink)
    newArchiveDate = self.urlDataExtractor.extractArchiveDateFromURL(newLink) #this newLink will be checked to see if it is worth saving for crawling
    newArchiveDate = datetime.datetime.strptime(newArchiveDate, '%Y%m%d%H%M%S') #reformat for comparison 
    usersChosenDate = datetime.datetime.strptime(self.searchDate, '%Y%m%d%H%M%S')

    self.logger.debug('Comparing --> newArchiveDate: ' + str(newArchiveDate) + ' usersChosenDate: ' + str(usersChosenDate))

    #check if this is the best match
    if newArchiveDate == usersChosenDate:
      self.logger.debug('MATCH')
      self.removePreviousSavedLink(newLinkFingerprint)  #remove the prior archived version of this link, newLink is better
      self.savedLinks.append(newLink)  #save this archived version of newLink instead
      savedLinksBestMatch.update({newLinkFingerprint:True})
      self.logger.debug('best match FOUND')
      return #no need to search further


    #keep searching: we have not found an exact match to user's selected archiveDate, get next best thing ie. oldest link we can find
    for savedLink in self.savedLinks:
      #keep oldest link
      savedLinkFingerprint = self.urlDataExtractor.extractURLFingerprint(savedLink)
      if not savedLinksBestMatch[savedLinkFingerprint]:
        if newArchiveDate < usersChosenDate:
          self.logger.debug('LESS THAN')
          self.removePreviousSavedLink(newLinkFingerprint)  #remove the prior archived version of this link, newLink is better
          #only replace if a match to user's selected archive data is not already saved there
          self.logger.debug('best match NOT found yet')
          self.savedLinks.append(newLink) #replace with older version (decided not to care about newer versions as we are going back in time anyway)
          savedLinksBestMatch.update({newLinkFingerprint:False})
          self.logger.debug('updated saved list with newlink: ' + newLink)



  ############################################################################
  # method: getLinksArchiveOrg
  # purpose: Search a given archive.org HTML page for other links on the page
  # note: a generic getLinks could not be used due to archive.org url formats
  ############################################################################
  def getLinksArchiveOrg(self, linkToCrawl, progressCounter):
    progressBar = '.' * progressCounter
    sys.stdout.write('%s' % (progressBar))
    sys.stdout.flush()

    mechanizePatch.monkeypatch_mechanize() #TODO: move into main class init method
    br = mechanize.Browser()
    br.set_handle_robots(False) #ignore robots.txt
    ua = 'ParameterPatrol'
    br.addheaders = [('User-Agent', ua), ('Accept', '*/*')]
    
    self.logger.debug('Started crawling of archive.org link: ' + linkToCrawl)	

    links = list() #list of found links to be crawled

    self.logger.debug('getLinksArchiveOrg()')
    self.logger.debug('self.crawledList size: ' + str(len(self.crawledList)))


    #check if link has been already crawled
    if linkToCrawl not in self.crawledList:
      try:
        self.logger.debug('opening ' + linkToCrawl)
        br.open(linkToCrawl)
        self.crawledList.append(linkToCrawl) #maintain list of crawled links

        #check we have a valid HTML page i.e. not a pdf, gif, etc
        if br.viewing_html(): 
          self.logger.debug('getLinksArchiveOrg(): found valid html page at: ' + linkToCrawl)
          for link in br.links():
            if not self.dataCheck.hasAsterix(link): #don't process any links containing an asterix (these are not related to user's chose archive date)
            
              # Limit crawling to the search year (yyyy)
              # This is because achive.org can have linked with mixed dates within a chosen archive.
              # This means that searching strictly on yyyymmddhhmmss can lead to cases where little or no results are found
              match = re.search(r'^/web/\d{4}', link.url)

              if match is not None:
                urlDate = str(match.group())[5:]
                if (self.searchDate.startswith(urlDate)):  #if yyyymmddhhmmss starts with yyyy
                  #limit crawling to user's chosen targetDomain
                  if (str(self.targetDomain) in link.url): 
                    self.logger.debug('Adding link to list: ' + link.url)
                    links.append(link.url)

                  #if user has supplied additional domain(s) to be included
                  elif self.includeDomainList:
                    for includeDomain in self.includeDomainList:
                      if(includeDomain in link.url):
                        self.logger.debug('Adding link to list: ' + link.url)
                        links.append(link.url)

                  #record any ignored domains so user can refine search if required
                  else:

                    #fully formed links with http(s)://
                    if "://" in link.url:
                      foundDomain = re.split(r"://", link.url)[1] #save text after http(s)://
                      #remove trailing /
                      if foundDomain.endswith('/'):
                        foundDomain = foundDomain[:-1] #remove last char from string
                      self.logger.debug('saving uncrawled domain: ', str(foundDomain))  
                      self.foundDomainsList.append(foundDomain) 

                    #no domain name contained in the link, ignore as we can't guess the fully qualified url
                    else:
                      pass

                  #if no additional domains provided by user, record all encountered domains for user incase inclusion is required when performing other searches
        else:
          print 'Skipping invalid HTML page: ', linkToCrawl
          self.crawledList.append(linkToCrawl) #take this link off the linksToCrawl list and ignore
          
      except: #catch exceptions that waybackmachine could not index
        print 'Could not crawl link: ', linkToCrawl
        self.crawledList.append(linkToCrawl) #take this link off the linksToCrawl list and ignore	
        pass

    #create unique list and return
    links = list(set(links))
    return links


  ###########################################################################################
  # method : crawl
  # purpose: crawl a regular site (non-archive.org) URL until no more new links can be found
  ###########################################################################################
  def crawl(self, url):  

    self.logger.debug('crawl(): ' + url)

    newLinks = list() #save a list of new links to crawl as they are discovered

    #make sure URL is fully formed
    url = self.setFullyQualifiedURL(url, self.nonArchiveOrgDomain)

    #check URL starts with http as a sanity check
    if url.startswith('http'):

      #do not descend into pages which are 3rd party included domains,
      #just add the single page to the list for parameter analysis later
      ###################################################################
      if any(domain in url for domain in self.includeDomainList):
        #simply add this page to the list for further processing, do not crawl further
        self.savedLinks.append(url)

      #iteratively crawl the link
      ###########################
      else:
        newLinks = self.getLinks(url, self.progressCounter)  #crawl this page for other links
        self.progressCounter += 1

        #iterate over newly found links to find more
        if newLinks: #check if not empty first
          for link in newLinks: 
            #make sure URL is fully formed
            link = self.setFullyQualifiedURL(link, self.nonArchiveOrgDomain)

            #check link has not already been crawled
            if link not in self.crawledList:
              self.savedLinks.append(link) #keep a record of all the crawled links
              self.crawl(link) #link is good to crawl

      #create a unique list of all saved crawled URLs
      self.savedLinks = list(set(self.savedLinks))


  ####################################################################################
  # method: getLinks
  # purpose: Search a regular (non-archive.org) HTML page for other links on the page
  ####################################################################################
  def getLinks(self, linkToCrawl, progressCounter):

    self.logger.debug('getLinks(): ' + linkToCrawl)

    progressBar = '.' * progressCounter
    sys.stdout.write('%s' % (progressBar))
    sys.stdout.flush()

    mechanizePatch.monkeypatch_mechanize() #TODO: move into main class init method
    br = mechanize.Browser()
    br.set_handle_robots(False) #ignore robots.txt
    ua = 'ParameterPatrol Tool'
    br.addheaders = [('User-Agent', ua), ('Accept', '*/*')]

    self.logger.debug('Started crawling of non archive.org link: ' + linkToCrawl)

    links = list() #list of found links to be crawled

    #check if link has been already crawled
    if linkToCrawl not in self.crawledList:
      try:
        br.open(linkToCrawl)
        self.crawledList.append(linkToCrawl) #maintain list of crawled links

        #check we have a valid HTML page i.e. not a pdf, gif, etc
        if br.viewing_html():
          for link in br.links():
            #limit crawling to user's chosen targetDomain
            if (str(self.targetDomain) in link.base_url):
              links.append(link.url)

            #if user has supplied additional domain(s) to be included
            elif self.includeDomainList:
              for includeDomain in self.includeDomainList:
                if(includeDomain in link.base_url):
                  links.append(link.url)

                #record any ignored domains so user can refine search if required
                else:

                  #fully formed links with http(s)://
                  if "://" in link.url:
                    foundDomain = re.split(r"://", link.url)[1] #save text after http(s)://
                    #remove trailing /
                    if foundDomain.endswith('/'):
                      foundDomain = foundDomain[:-1] #remove last char from string
                    self.foundDomainsList.append(foundDomain)

                  #no domain name contained in the link, ignore as we can't guess the fully qualified url
                  else:
                    self.logger.debug('no domain name contained in the link: ' + link.url)
                    pass

            #if no additional domains provided by user, record all encountered domains for user incase inclusion is required when performing other searches
            else:

              #fully formed links with http(s)://
              if "://" in link.url:
                foundDomain = re.split(r"://", link.url)[1] #save text after http(s)://
                #remove trailing /
                if foundDomain.endswith('/'):
                  foundDomain = foundDomain[:-1] #remove last char from string
                self.foundDomainsList.append(foundDomain)

              #no domain name contained in the link, ignore as we can't guess the fully qualified url
              else:
                pass

        else:
          print 'Skipping invalid HTML page: ', linkToCrawl
          self.crawledList.append(linkToCrawl) #take this link off the linksToCrawl list and ignore

      except (mechanize.HTTPError, mechanize.URLError) as e: 
        print 'Could not crawl link: ', linkToCrawl
        self.logger.exception(str(e))
        self.crawledList.append(linkToCrawl) #take this link off the linksToCrawl list and ignore 
        pass

    #create unique list and return
    links = list(set(links))
    return links



  ############################################################################################################
  # method: setFullyQualifiedURL
  # purpose: make sure a URL is fully qualified with a http(s)://domain/ prefix
  #          this is to catch cases where links are just to the page name e.g. "<a href="page1.html">
  #          not considering subdomains here (-i argument), assuming they belong to main domain (-t argument)
  ############################################################################################################
  def setFullyQualifiedURL(self, url, domain):
    fqurl = url 

    self.logger.debug('setFullyQualifiedURL(): domain= ' + domain)
    self.logger.debug('setFullyQualifiedURL(): url= ' + url)

    if fqurl.startswith(domain):
      pass #ignore fully formed urls

    #for cases where "http://domain" & "url"
    elif (not domain.endswith('/')) and (not url.startswith('/')):
      fqurl = domain + "/" + url
      
    #for cases where "http://domain/" & "/url"
    elif domain.endswith('/') and url.startswith('/'):
      domain = domain.rstrip('/') #remove trailing /
      fqurl = domain + url

    #for cases where "http://domain/" & "url", "http://domain" & "/url"
    else:
      fqurl = domain + url

    self.logger.debug('setFullyQualifiedURL(): fqurl= ' + fqurl)
    return fqurl

