import logging
import re
import os
import shutil
import sqlite3
import sys
import urlDataExtractor

from tabulate import tabulate
from collections import defaultdict

###############################################################
# Class: Results
# Purpose: Data structures for holding results during spidering
#          & Functions for saving results to sqlite database
###############################################################
class Results():

  def __init__(self, targetDomain):

    #logging
    self.logger = logging.getLogger(__name__)

    self.getParametersDictionary = defaultdict(dict) #dictionary of GET parameters list per unique page
    self.postParametersDictionary = defaultdict(dict) #dictionary of POST parameters per unique page

    #user's chosen target domain
    self.targetDomain = targetDomain
    
    #sqlite3 connection
    self.conn = None
    self.cur = None

    #project database
    self.projectDirectory = None
    self.projectDatabase = None

    #functions for extracting data from URLs
    self.urlDataExtractor = urlDataExtractor.URLDataExtractor()

  #create new database for holding results
  def openDatabase(self, directoryName, databaseName):

    self.projectDirectory = directoryName

    #first, create directory for storing results database
    directory = os.path.dirname(self.projectDirectory)

    if not os.path.exists(self.projectDirectory):
      os.makedirs(self.projectDirectory)
 
    #next, create the database
    if directory is not None:
      self.projectDatabase = self.projectDirectory + '/' + databaseName
    else:
      self.projectDatabase = databaseName

    #create database connection
    self.logger.info('Creating ' + self.projectDatabase + ' to store results.')
    self.conn = sqlite3.connect(self.projectDatabase)


  def closeDatabase(self):
    self.logger.debug('Entering closeDatabase()')
    self.conn.close()

    

  #Save URL parameters to URLParameters table
  ###########################################
  def writeURLParamsToDatabase(self, archiveOrgUrl, host, url, pageName, parameters):

      for row in parameters: 
        paramName = row[0]
        paramValue =  row[1]

        #check for missing values
        if archiveOrgUrl is None:
          archiveOrgUrl = "[missing value]"
          self.logger.debug('Writing url paramters to database: no value found for archiveOrgUrl')
        if host is None:
          self.logger.debug('Writing url paramters to database: no value found for host')
          host = "[missing value]"
        if url is None:
          self.logger.debug('Writing url paramters to database: no value found for url')
          url = "[missing value]"
        if pageName is None:
          self.logger.debug('Writing url paramters to database: no value found for pageName')
          pageName = "[missing value]"
        if paramName is None:
          self.logger.debug('Writing url paramters to database: no value found for paramName')
          paramName = "[missing value]"
        if paramValue is None:
          self.logger.debug('Writing url paramters to database: no value found for paramValue')
          paramValue = "[missing value]"

        #write to database
        self.cur.execute('INSERT INTO URLParameters VALUES (?, ?, ?, ?, ?, ?)', (str(archiveOrgUrl), str(host), str(url), str(pageName), str(paramName), str(paramValue)))

        self.conn.commit()

 
  #Save FORM paramters to database
  ################################

  def writeFormParamsToDatabase(self, archiveOrgUrl, host, url, pageName, parameters, key):
    self.logger.debug('writeFormParamsToDatabase() fileName: ' + pageName)

    formName = key[1]
    URL = key[0]

    for row in parameters: 
      paramName = row[0]
      paramDefaultValue =  row[1]
      paramType =  row[2]

      #check for missing values
      if archiveOrgUrl is None:
        archiveOrgUrl = "[missing value]"
        self.logger.debug('Writing url paramters to database: no value found for archiveOrgUrl')
      if host is None:
        self.logger.debug('Writing url paramters to database: no value found for host')
        host = "[missing value]"
      if url is None:
        self.logger.debug('Writing url paramters to database: no value found for url')
        url = "[missing value]"
      if pageName is None:
        self.logger.debug('Writing url paramters to database: no value found for pageName')
        pageName = "[missing value]"
      if paramName is None:
        self.logger.debug('Writing url paramters to database: no value found for paramName')
        paramName = "[missing value]"
      if paramDefaultValue is None:
        self.logger.debug('Writing url paramters to database: no value found for paramDefaultValue')
        paramValue = "[missing value]"
      if paramType is None:
        self.logger.debug('Writing url paramters to database: no value found for paramType')
        paramValue = "[missing value]"

      #write to database
      self.cur.execute('INSERT INTO FormParameters VALUES (?, ?, ?, ?, ?, ?, ?, ?)',  (str(archiveOrgUrl), str(host), str(url), str(pageName), str(formName), str(paramName), str(paramDefaultValue), str(paramType)))
      
      self.conn.commit()


  #save GET and POST parameters
  def saveParameters(self):
    self.logger.debug('Entering saveParameters()')
    self.logger.debug('size of self.getParametersDictionary is: ' + str(len(self.getParametersDictionary)))
    self.logger.debug('size of self.postParametersDictionary is: ' + str(len(self.postParametersDictionary)))

    #print GET parameters from URL
		##############################
    isGet = True

    with self.conn:
      self.cur = self.conn.cursor()
      self.cur.execute('DROP TABLE IF EXISTS URLParameters')
      self.cur.execute('CREATE TABLE URLParameters(FullUrl, Host, URL, PageName, ParameterName, ParameterValue)') 
      
      for key in self.getParametersDictionary:
        if self.getParametersDictionary[key] is not None:
          self.logger.debug('saveParameters(): self.getParametersDictionary[key] = ' + str(self.getParametersDictionary[key]))

          urlLink = key
    
          archiveOrgUrl = str(urlLink) 
          host = self.urlDataExtractor.extractDomainFromURL(urlLink) 
          url = self.urlDataExtractor.extractURLFromURL(urlLink)
          pageName = self.urlDataExtractor.extractFilenameFromURL(urlLink)
          
          self.logger.debug('writing GET paramters to db for: ' + str(self.getParametersDictionary))
          self.writeURLParamsToDatabase(archiveOrgUrl, host, url, pageName, self.getParametersDictionary[key])

	
      #print POST parameters from form
      ################################
      self.cur.execute('DROP TABLE IF EXISTS FormParameters')
      self.cur.execute('CREATE TABLE FormParameters(FullUrl, Host, URL, PageName, FormName, ParameterName, ParameterDefaultValue, ParameterType)')
 
      for key in self.postParametersDictionary:
        if self.postParametersDictionary[key] is not None:
          if (key[0] is not None) and (key[1] is not None):

            url = key[0]
        
            fileName = key[0]
            formName = key[1]
            archiveOrgUrl = str(url)
            host = self.urlDataExtractor.extractDomainFromURL(url)
            url = self.urlDataExtractor.extractURLFromURL(url)
            pageName = self.urlDataExtractor.extractFilenameFromURL(fileName)

            self.logger.debug("\t" + str(self.postParametersDictionary[key]))
            self.logger.debug(str(self.postParametersDictionary[key]))
            self.logger.debug('pageName= ' + pageName)

            if fileName is not None: 
              self.logger.debug('writing POST paramters to db for: ' + str(self.postParametersDictionary))
              self.writeFormParamsToDatabase(archiveOrgUrl, host, url, pageName, self.postParametersDictionary[key], key)


