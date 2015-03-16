######################################################################################
# class: LinkConsumer
# purpose: consumes items in the outQueue and sends to parameterFetcher for processing
######################################################################################

import logging
import Queue
import threading
import parameterFetcher
import results

class LinkConsumer(threading.Thread):

  def __init__(self, outQueue, projectDirectory, results):

    threading.Thread.__init__(self)
    self.outQueue = outQueue
    self.projectDirectory = projectDirectory

    #data storage
    self.results = results

    #logging
    self.logger = logging.getLogger(__name__)

  def run(self):
    while True:
      page = self.outQueue.get()
      
      self.logger.debug('Consumer: getting parameters for ' + page)
      
      paramFetcher = parameterFetcher.ParameterFetcher(page, self.projectDirectory)
      paramFetcher.saveParameters(self.results) #parse parameters
      
      self.outQueue.task_done()
