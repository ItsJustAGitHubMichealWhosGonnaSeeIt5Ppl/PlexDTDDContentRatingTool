import requests
import urllib.parse
import json
import os
import emoji
import sqlite3
import re
from modules.Plex import getPlexItem,getPlexTV
from modules.DTDD import dtddSearch, dtddComments
from modules.other import confidenceScore, mediaDictCreator, descriptionCreator, seriesCleaner
from datetime import date, datetime
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
Comments
- "[Comment Here]"

dtddID[]
LastUpdated[]
"""

DTDD_QUERY_URL = 'https://www.doesthedogdie.com/dddsearch?q='
DTDD_ID_URL = 'https://www.doesthedogdie.com/media/'
DTDD_KEY = os.getenv('DTDD_KEY')
PLEX_URL = os.getenv('PLEX_URL') + ":32400/"
PLEX_KEY = os.getenv('PLEX_KEY')


excludedLibraries = ['10','13','14','4', '1']
triggerIDWarn = [201,326]
TriggerIDAlert = [182,292]
triggerIDList = triggerIDWarn + TriggerIDAlert
# define names for triggers to be displayed as.
triggerSafeNames = {
    182: 'Sexual Assualt',
    201: 'Vomitting',
    292: 'Rape',
    299: 'Drugged',
    320: 'Pedo',
    326: 'Rape Mentioned',
}

""" Trigger List (clean up later) - I DID NOT RANK THESE THIS IS THE TOPIC IDS FROM DTDD
TopicId = Topic Name < Key
    182 = Sexual Assualt (Onscreen?) / Alert
    201 = Vomitting / Warn
    292 = Rape Onscreen / Alert
    299 = Drugged / Warn
    320 = Pedo / Warn
    326 = Rape Mentioned / Warn
"""

# Optimised Media list creation
# TODO #13 Consider combinining the scanning of shows and media. Only add items with changes to the list
mediaList = {}
for libraryID, libInfo in getPlexItem('libraries').items():
    if str(libraryID) in excludedLibraries:
        print('skipping excluded library')
        continue
    for itemID in getPlexItem('libraryItems',libraryID):
        item = getPlexItem('libraryItem',itemID['ratingKey'])
        # Extract GUID Tags for matching later
        guidDict = {}
        trackID = ''
        if 'Guid' in item.keys(): # Prevents failure if item has just been added and not yet matched
            for ids in item['Guid']:
                guidDict[ids['id'].split('://')[0]] = ids['id'].split('://')[1]        
        mediaList[item['ratingKey']] = mediaDictCreator(item,'default',gDict=guidDict,libID=libraryID,libInf=libInfo['libraryType'])

                   
# Check media
for item in mediaList.values():
    triggersPresent = {}
    if item['hasDTDD'] == False: # Search DTDD if no DTDD ID is available.
        search = dtddSearch(item['title'])
        dtddID = confidenceScore(item,search)
        if dtddID == 'No results':
            mediaList[item['itemID']].update({'triggers': 'Unknown'})
            continue #TODO #8 Create string explaining media could not be found
        dtddConf = dtddID[1]
        dtddID = dtddID[0]['id']
        if dtddConf == 100: # 100 confident that media match is correct
            mediaList[item['itemID']].update({'dtddID': dtddID}) 
    else: # Temporary 
        dtddID = item['dtddID']
    
    # Check if media even needs to be updated
    # Date format: '2023-11-13T03:28:18.000Z'
    
    dtddItem = dtddSearch(dtddID,'E')
    
    if  item['hasDTDD'] == True and datetime.fromisoformat(dtddItem['item']['updatedAt']) < datetime.fromisoformat(item['dtddLastUpdated']):
        continue #TODO #9 Update description with new date, change nothing else.
    
    # Check for triggers
    for triggerGroups in dtddItem['allGroups']:
            for triggerTopics in triggerGroups['topics']:
                if triggerTopics['TopicId'] in triggerIDList and triggerTopics['yesSum'] > triggerTopics['noSum']:
                    triggersPresent[triggerTopics['TopicId']] = {
                        'yes': triggerTopics['yesSum'],
                        'no': triggerTopics['noSum'],
                    }
    # Add new information to mediaList dictionary
    mediaList[item['itemID']].update({'triggers': triggersPresent if len(triggersPresent) > 0 else 'None','dtddLastChecked': 'today'})    
    if len(triggersPresent) == 0:
        continue # Safe 
    
    # Check if item is TV show, will effect comment scanning.
    if item['itemType'] == 'show': # TODO #10 Only scan all episode content if show gets flagged
        showInfo = getPlexTV(item['itemID'])
        mediaList[item['itemID']].update({'seasons': showInfo})
    
        
    def numNormaliser(inputNum):
        """ Creates consistent numbers for Season and Episode values 1 becomes 01, returned in string form
        """
        return str(inputNum) if inputNum > 9 else '0' + str(inputNum)
    # Check comments
    for tID in item['triggers']: # Eventually I will shorten all of this but having it split up is helpful for debugging (for me)
        comments = dtddComments(item["dtddID"],tID)
        for comment in comments:
            # Create comment string
            rating = ('' if item['itemType'] != 'show' else f'S{numNormaliser(comment["index1"])}E{numNormaliser(comment["index2"])} | ' if comment['index1'] != -1 else 'S??E?? | ') + f'TID[{tID}] | ' + f':thumbs_up: {comment["yes"]} / {comment["no"]} :thumbs_down:' if comment['isVerified'] == False else f':check_mark_button:'
            text = comment['comment']
            # This will be optimised and cleaned up later TODO #11 Optimise this
            # Add triggerstring to series + seasons and episodes if present.
            mediaList[item['itemID']]['comments'].append(f'{rating} {text}')
            if item['itemType'] == 'show' and comment['index1'] in mediaList[item['itemID']]['seasons']:
                seasonPath = mediaList[item['itemID']]['seasons'][comment["index1"]]
                seasonPath['triggers'].append(tID if tID not in seasonPath['triggers'] else None) # Add triggers as they are only added to series during initial scans.
                seasonPath['comments'].append(f'{rating} {text}')
                if comment['index2'] in mediaList[item['itemID']]['seasons'][comment["index1"]]['episodes']:
                    episodePath = mediaList[item['itemID']]['seasons'][comment["index1"]]['episodes'][comment["index2"]]
                    episodePath['triggers'].append(tID if tID not in episodePath['triggers'] else None) # Add triggers as they are only added to series during initial scans.
                    episodePath['comments'].append(f'{rating} {text}')
    
    # From here on we are working under the assumption only items that need to be updated will be present
    
    
    
    if item['itemType'] == 'show':
        seriesCleaner(item)
    
    print(descriptionCreator(item,triggerSafeNames))    
    
    
    print(f'No matching media type for {item["itemType"]}')
print('test')