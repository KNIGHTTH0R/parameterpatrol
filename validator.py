import re

################################################
# Class: Validator
# Purpose: perform basic data validation checks
################################################

class Validator():

  #check if an object is empty
  def isEmpty(self, obj):
    if obj == None:
      return True
    elif obj == "":
      return True
    elif not obj:
      return True
    else:
      return False

  #check the length of an object
  def isCorrectLength(self, obj, length):
    if len(str(obj)) == length:
      return True
    else:
      return False

  #check if a numeric is in range
  def inRange(self, number, numberStart, numberEnd):
    if (number <= numberEnd) and (number >= numberStart):
      return True
    else:
      return False

  #check if an object is an integer
  def isInteger(self, obj):
    if isinstance(obj, (int)):
      return True
    else:
      return False

  #check if a string contains an asterix
  def hasAsterix(self, string):
    if re.search(r'\*', str(string)) is not None:
      return True
    else:
      return False
