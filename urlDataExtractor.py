import logging

#################################################################
# Class: URLDataExtractor
# Purpose: provide basic functions for extracting data from URLs
# No regex foo shall pass here, it's all very lame regex  
#################################################################

class URLDataExtractor():

  def __init__(self):
    #logging
    self.logger = logging.getLogger(__name__)


  # method: extractWebDirectoryFromURL
  # purpose: extract the web directory location from a URL
  # i.e. by extracting out the "/[dirname]" from a url such as:
  # http(s)://archive.org/http://web.archive.org/web/[yyyymmddhhmmss]/http(s)://domain.com/[dirname]/pagename.html?param1=1&param2=2
  ##############################################################################################################
  def extractWebDirectoryFromURL(self, url):

    webDir = None

    #extract everthing after last http(s)://
    #e.g. archive.org urls have contain more than 1 http(s)://
    beforeKeyword, keyword, afterKeyword = url.partition('//')
    webDir = url.rsplit('//', 1)[-1]

    #remove domain portion ie. remove domain.com from url: "domain.com/[dirname]/pagename.html"
    beforeKeyword, keyword, afterKeyword = webDir.partition('/')
    webDir = "/" + afterKeyword  #keep leading / e.g. for root directories

    #remove any trailing parameters
    webDir = webDir.rsplit('?', 1)[0]

    #remove everything after last / i.e. pagename and parameters
    webDir = webDir.rsplit('/', 1)[0]
    webDir = webDir + "/"  #append trailing / e.g. for root directories which would be blank
    
    return webDir


  # method: extractURLFromURL
  # purpose: extract the url location from an archive.org URL
  # i.e. by extracting out the "/[dirname]/pagename.html?param1=1&param2=" from a url such as:
  # http(s)://archive.org/http://web.archive.org/web/[yyyymmddhhmmss]/http(s)://domain.com/[dirname]/pagename.html?param1=1&param2=2
  ##############################################################################################################
  def extractURLFromURL(self, url):

    fullUrl = None

    #extract everthing after last http(s)://
    #e.g. archive.org urls have contain more than 1 http(s)://
    beforeKeyword, keyword, afterKeyword = url.partition('//')
    fullURL = url.rsplit('//', 1)[-1]

    #remove domain portion ie. remove domain.com from url: "domain.com/[dirname]/pagename.html"
    beforeKeyword, keyword, afterKeyword = fullURL.partition('/')
    fullURL = "/" + afterKeyword  #keep leading / e.g. for root directories

    #remove any trailing /
    if fullURL.endswith('/'):
      fullURL = fullURL[:-1]

    if not fullURL:
      fullURL = '/' #cases where there is no directory, just use /

    return fullURL


  # method: extractDomainFromURL
  # purpose: extract the host from a URL
  # i.e. by extracting out the "domain.com" from a url such as:
  # http(s)://archive.org/http://web.archive.org/web/[yyyymmddhhmmss]/http(s)://domain.com/[dirname]/pagename.html?param1=1&param2=2
  ##############################################################################################################
  def extractDomainFromURL(self, url):

    domain = None
  
    #extract everthing after last http(s)://
    #e.g. archive.org urls can contain more than 1 http(s)://
    beforeKeyword, keyword, afterKeyword = url.partition('//')

    domain = afterKeyword

    #cater for https://domain
    if 'https://' in domain:
      beforeKeyword, keyword, afterKeyword = domain.partition('https://')
      domain = afterKeyword
    elif 'http://' in domain:
      beforeKeyword, keyword, afterKeyword = domain.partition('http://')
    
    domain = afterKeyword


    #remove everything after first / i.e. directories and parameters
    domain = domain.split('/', 1)[0]

    return domain


  # method: extractFilepathFromURL
  # purpose: extract the file path from a URL
  # i.e. by extracting out the "domain.com/[dirname]/pagename.html" from a url such as:
  # http(s)://archive.org/http://web.archive.org/web/[yyyymmddhhmmss]/http(s)://domain.com/[dirname]/pagename.html?param1=1&param2=2
  ##############################################################################################################
  def extractFilepathFromURL(self, url):

    filePath = None
  
    #extract everthing after last http(s)://
    #e.g. archive.org urls can contain more than 1 http(s)://
    beforeKeyword, keyword, afterKeyword = url.partition('//')
    filePath = url.rsplit('//', 1)[-1]

    return filePath


  # method: extractFilenameFromURL
  # purpose: extract the file name from a URL
  # i.e. by extracting out the "pagename.html" from a url such as: 
  # http(s)://archive.org/http://web.archive.org/web/[yyyymmddhhmmss]/http(s)://domain.com/[dirname]/pagename.html?param1=1&param2=2
  ##############################################################################################################
  def extractFilenameFromURL(self, url):

    fileName = None
    filePath = self.extractFilepathFromURL(url)

    #start working on pulling out the fileName...
    fileName = filePath

    #check is there is no / directly before ? (unlikely but could happen)
    #e.g. http://domain.com/page1.html/?param1=value1
    if "/?" in fileName:
      fileName = fileName.replace("/?", "?")

    #remove any trailing /
    if fileName.endswith('/'):
      fileName = fileName[:-1]

    #strip everything after last /
    if "/" in fileName:
      fileName = fileName.rsplit('/', 1)[-1]
    else:
      fileName = "/"

    #remove any parameters
    fileName = fileName.rsplit('?', 1)[0]

    #check fileName contains a .* extension, otherwise it could be a dir e.g. http://web.archive.org/web/[yyyymmddhhmmss]/http(s)://domain.com/dirname
    if '.' not in fileName:
      fileName = '/'  #there is no fileName, just set to dir /

    return fileName


  # method: extractFilenameAndParametersFromURL
  # purpose: extract the file name and paramters from a URL
  # i.e. by extracting out the "pagename.html?param1=1&param2=2" from a url such as: 
  # http(s)://archive.org/http://web.archive.org/web/[yyyymmddhhmmss]/http(s)://domain.com/[dirname]/pagename.html?param1=1&param2=2
  ##############################################################################################################
  def extractFilenameAndParametersFromURL(self, url):

    fileName = None
    filePath = self.extractFilepathFromURL(url)

    #start working on pulling out the fileName...
    fileName = filePath

    #check is there is no / directly before ? (unlikely but could happen)
    #e.g. http://domain.com/page1.html/?param1=value1
    if "/?" in fileName:
      fileName = fileName.replace("/?", "?")

    #remove any trailing /
    if fileName.endswith('/'):
      fileName = fileName[:-1]

    #strip everything after last /
    fileName = fileName.rsplit('/', 1)[-1]

    return fileName



  # method: extractArchiveDateFromURL
  # purpose: extract the archive data from an archive.org URL
  # i.e. the [yyyymmddhhmmss] from a url such as:
  # http(s)://archive.org/http://web.archive.org/web/[yyyymmddhhmmss]/http(s)://domain.com/[dirname]/pagename.html?param1=1&param2=2
  ##############################################################################################################
  def extractArchiveDateFromURL(self, url):
    archiveDate = None

    beforeKeyword, keyword, afterKeyword = url.partition('web.archive.org/web/')
    beforeKeyword, keyword, afterKeyword = afterKeyword.partition('/')
    archiveDate = beforeKeyword

    return archiveDate

  
  # method:
  # Remove this portion from archive.org domain urls: http(s)://archive.org/http://web.archive.org/web/[yyyymmddhhmmss]/
  # so we are left with a unique portion of the url for indexing: 
  # http(s)://domain.com/[dirname]/pagename.html?param1=1&param2=2
  ##############################################################################################################
  def extractURLFingerprint(self, url):

    filePath = None
  
    #extract everthing after last http(s)://
    #e.g. archive.org urls can contain more than 1 http(s)://
    beforeKeyword, keyword, afterKeyword = url.partition('//')

    #lamest regex ever...
    #perserve the "s" if url was http"s"://
    filePath = url.rsplit('/http', 1)[-1]
  
    filePath = 'http' + filePath #put back http in front of :// or "s"://

    #remove any trailing /
    if filePath.endswith('/'):
      filePath = filePath[:-1]

    return filePath

  
