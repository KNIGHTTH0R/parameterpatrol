import logging
import mechanize
import mechanizePatch
import re

from urlparse import urlparse, parse_qs
from tabulate import tabulate
from collections import defaultdict

class ParameterFetcher:

  def __init__(self, url, projectDirectory):

    #logging
    self.logger = logging.getLogger(__name__)

    self.url = url
    self.projectDirectory = projectDirectory
    
  def saveParameters(self, results):
    mechanizePatch.monkeypatch_mechanize()
    br = mechanize.Browser()
    br.set_handle_robots(False) #ignore robots.txt
    
    try:
      self.logger.debug('Fetching forms from: ' + self.url)
      response = br.open(self.url)

      pageName = str(self.url)
      if re.match(r'^.*\?', pageName) is not None:
        pageName = re.match(r'^.*\?', pageName).group(0) #remove trailing parameters
        pageName = pageName[:-1] #remove last char "?"

        self.logger.debug('pageName: ' + pageName)

			#SAVE GET PARAMETERS FROM URL
			#############################
      parameters = urlparse(self.url).query
      dataRow=[]
      dataRows=[]
      if parameters: #save if not empty
        parameters = re.split('&', parameters) #split parameters based on "&"
        for param in parameters:
          dataRow = []
          if (param.find('=') == -1): #if url param passed with no value, set to "no value" for pretty printed table
            value = "[no value]"
            param = re.split('=', param) #split name:values based on "="
            param.append(value)
            dataRow = param
          else: #name:value pair exists
            paramValuePair = re.split('=', param) #split name:values based on "="
            dataRow = paramValuePair
            self.logger.debug('found GET param: ' + str(dataRow))
          dataRows.append(dataRow) #keep track of all URL params for pretty printed table
        results.getParametersDictionary[pageName] = dataRows

			#SAVE POST PARAMETERS FROM FORMS
			################################
			#header and rows for pretty printed table
      header = []
      dataRow = []
      dataRows = []
      try:
        for form in br.forms():
          header = ["Name", "Default Value", "Type"]
          for control in form.controls:
            paramType = "[no value]" if (control.type.strip is '' or control.type.strip is None) else control.type
            paramName = "[no value]" if (control.name is '' or control.name is None) else control.name
            paramValue = "[no value]" if (control.value is '' or control.value is None) else control.value
            
            dataRow = [paramName, paramValue, paramType]
            dataRows.append(dataRow) #keep track of all rows for pretty printed table
            self.logger.debug('found POST param: ' + str(dataRow))
          results.postParametersDictionary[pageName, form.name] = dataRows
          dataRow = []
          dataRows = []
      except:
        self.logger.exception('Cannot parse forms on ' + pageName)
        pass
          
    except (mechanize.HTTPError, mechanize.URLError) as e:
      self.logger.exception('Could not find page to analyse at ' + self.url + str(e))


