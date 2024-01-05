import requests
import urllib.parse
import json
import os
import emoji
import sqlite3
import re
from modules.Plex import getPlexItem
# Will need DB for the following
## Media Libraries
### ID / Library Name / Library Type / DTDD Relevant tag
## Media
### Media Name / Media ID / DTDD ID / Media Type ID 


""" MAJOR REVAMP NEEDED
Each library is checked and trigger strings are created.  Once done, these will all be sent to plex at once to update.



This will be the ammended description
== DTDD Information ==
Triggers:
Comments:
- "[Comment Here]"

dtddID[]
LastUpdated[]
"""

DTDD_QUERY_URL = 'https://www.doesthedogdie.com/dddsearch?q='
DTDD_ID_URL = 'https://www.doesthedogdie.com/media/'
DTDD_KEY = os.getenv('DTDD_KEY')
PLEX_URL = os.getenv('PLEX_URL') + ":32400/"
PLEX_KEY = os.getenv('PLEX_KEY')


excludedLibraries = ['10','13','14','4']
triggerIDWarn = [201,326]
TriggerIDAlert = [182,292]
triggerIDList = triggerIDWarn + TriggerIDAlert


""" Trigger List (clean up later) - I DID NOT RANK THESE THIS IS THE TOPIC IDS FROM DTDD
TopicId = Topic Name < Key
    182 = Sexual Assualt (Onscreen?) / Alert
    201 = Vomitting / Warn
    292 = Rape Onscreen / Alert
    299 = Drugged / Warn
    320 = Pedo / Warn
    326 = Rape Mentioned / Warn
"""

mediaDict = {
    '@mediaID': {
        'mediaType': 'show/movie',
        'seasonID': 'only for shows',
        'showID':'only for shows',
        'triggers': ['triggerlist'],
        'comments': ['commentlist'],
        'lastUpdated': 'nowdate'
        }
    }

"""  """

# Regex queries to be used when finding media information.
dtddRE = re.compile('dtddID\\[(.*?)\\]')
lastUpdateRE = re.compile('lastUpdated\\[(.*?)\\]')

# Optimised Media list creation
mediaList = {}
for libraryID in getPlexItem('libraries'):
    if str(libraryID) in excludedLibraries:
        print('skipping excluded library')
        continue
    for itemID in getPlexItem('libraryItems',libraryID):
        item = getPlexItem('libraryItem',itemID)
        # Extract GUID Tags for matching later
        guidDict = {}
        trackID = ''
        for ids in item['Guid']:
            guidDict[ids['id'].split('://')[0]] = ids['id'].split('://')[1]
        hasDTDD = True if '== DTDD Information ==' in item['summary'] else False
        mediaList[item['ratingKey']] = {
            'libraryID': libraryID,
            'itemID': item['ratingKey'],
            'GUID': item['guid'], 
            'title': item['title'],
            'description':item['summary'],
            'releaseYear': item['year'],
            'mediaTypeTrue': item['type'],
            'dbIDs': guidDict, # Helps when matching media
            'hasDTDD': hasDTDD, # True/False.
            'dtddID':dtddRE.search(item['summary']).group(1) if hasDTDD == True else False, # Only filled in if hasDTDD is True. 
            'dtddLastChecked':lastUpdateRE.search(item['summary']).group(1) if hasDTDD == True else False, # Only filled in if hasDTDD is True. Shows last date that information was checked for this item
            'descriptionClean':item['summary'].split('== DTDD Information ==') if hasDTDD == True else False # Only filled in if hasDTDD is True.  Description without the DTDD warnings, helpful when recreating it later
        }
# Check media

for x in mediaList:
    print(x)