import requests
import urllib.parse
import json
import os
import emoji
import sqlite3
import re
# Will need DB for the following
## Media Libraries
### ID / Library Name / Library Type / DTDD Relevant tag
## Media
### Media Name / Media ID / DTDD ID / Media Type ID 

DTDD_QUERY_URL = 'https://www.doesthedogdie.com/dddsearch?q='
DTDD_ID_URL = 'https://www.doesthedogdie.com/media/'
DTDD_KEY = os.getenv('DTDD_KEY')
PLEX_URL = os.getenv('PLEX_URL') + ":32400/"
PLEX_KEY = os.getenv('PLEX_KEY')

# TODO #1 Move me to a place where I can be changed easily
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

#TODO #2 Add TMDB API to check more information
def dtddLookup(ID):
    headers = {
    'Accept': 'application/json',
    'X-API-KEY': DTDD_KEY
    }
    response = requests.get(DTDD_ID_URL + str(ID) ,headers = headers)
    if response.status_code == 200 and len(json.loads(response.content)['item']) > 0:
        return json.loads(response.content)
    else:
        return f'Failed to find item'


def queryDTDD(query):
    # DTDD Search (by title)
    headers = {
    'Accept': 'application/json',
    'X-API-KEY': DTDD_KEY
    }
    response = requests.get(DTDD_QUERY_URL + query ,headers = headers)
    if response.status_code == 200 and len(json.loads(response.content)['items']) > 0:
        return json.loads(response.content)
    else:
        return f'No results'


def mediaCheck(plexitem):
    #Check media and compare search results with original file. Return info based on confidence level.
    """ Compare Order - Confidence score (update as needed) Mark anything that confidence score is below 80% No match below 65%
    Confidence score rang (0 - 100)
    IMDB ID - 100
    TMDB ID - 100
    itemType - 10

    Director - 30
    Actor(s) - 30
    Release Year - 25(?) (-5 if +or- 1 year)
    Title - 20(?)
    Genre - 25(?)
    """
    dtddResults = queryDTDD(plexitem['title'])
    if dtddResults == 'No results': # Pass dtdd response down
        return dtddResults

    def updatePlexItem(mediaDetails,TriggerIDs):
        def triggerString(IDs):
            eWarn = warn = alert = False
            tString = ''
            for ID in IDs:
                if int(ID) in triggerIDWarn:
                    if int(ID) == 201:
                        eWarn = True # Extra warning for single user 
                    else:
                        warn = True
                if int(ID) in TriggerIDAlert:
                    alert = True
            if alert == True:
                tString += f':cross_mark: - M '
            elif warn == True:
                tString += f':warning: - M '
            if eWarn == True:
                tString += f':warning: - E'
            if alert == False and warn == False and eWarn == False:
                tString = f':check_mark:'
            return emoji.emojize(tString)
        if TriggerIDs == 'Unknown':
            ValueString = emoji.emojize('? NO DATA ?')
        elif TriggerIDs == 'Safe':
            ValueString =  emoji.emojize(':check_mark:')
        else:
            ValueString = triggerString(TriggerIDs)
        request = f'library/sections/{mediaDetails["libraryID"]}/all?type=1&id={mediaDetails["itemID"]}&includeExternalMedia=1&contentRating.value={ValueString}'
        attemptUpdate = requests.put(PLEX_URL + request, headers=headers)
        print(attemptUpdate.status_code)

    def mediaMatch(mediaItem,searchResults):
        confidence = 0
        # Create confidence score for results.
        for result in searchResults['items']:
            confidence = 0
            while confidence < 100:
                if mediaItem['mediaTypeTrue'] != 'show':
                    if str(result['tmdbId']) == str(mediaItem['dbIDs']['tmdb']):
                        confidence += 100
                        break
                else:
                    try:
                        if str(result['tmdbId']) == str(mediaItem['dbIDs']['tmdb']):
                            confidence += 100
                            break
                    except:
                        pass
                if str(result['imdbId']) == str(mediaItem['dbIDs']['imdb']):
                    confidence += 100
                    break
                if result['name'].lower() == mediaItem['title'].lower():
                    confidence += 20
                # if result['genre'].lower() in mediaItem['Genre'].lower():
                #     confidence += 25
                if result['releaseYear'].isnumeric():
                    if int(result['releaseYear']) == int(plexitem['releaseYear']):
                        confidence += 25
                    # Sometimes DTDD will return 'unknown' for the year. #TODO #3 Add better failure prevention to the confidence checker
                    elif int(result['releaseYear']) == int(plexitem['releaseYear'])+1 or int(result['releaseYear']) == int(plexitem['releaseYear'])-1:
                        confidence += 20
                break
            if confidence >= 100:
                return result
            # Failed to find match
        return 'No results'
        


    
    result = mediaMatch(plexitem,dtddResults)
    try:
        resultDict = json.loads(result['stats'])['topics']
    except:
        resultDict = False
    if result != 'No results' and resultDict !=False:
        safe = 0
        conflict = 0
        triggersPresent = []
        detailedResult = dtddLookup(result['id'])
        for groups in detailedResult['allGroups']:
            for items in groups['topics']:
                if items['TopicId'] in triggerIDList:
                    yesSum = items['yesSum']
                    noSum = items['noSum']
                    if yesSum == 0 and noSum == 0: # Unsure
                        print('No data')
                    elif (yesSum > noSum and noSum == 0) or (yesSum > noSum and yesSum/noSum > 1.5): # Trigger is present
                        triggersPresent.append(items['TopicId'])
                    elif (yesSum == 0 and noSum > 0) or (noSum > yesSum) or noSum/yesSum > 1.5: #Tigger not present
                        safe += 1 
                    elif noSum/yesSum > 1 and noSum/yesSum < 1.5: # Conflicting response
                        conflict += 1
                    else:
                        print('unknown')
                    print(items['comment'])
        if len(triggersPresent) > 0:
            updatePlexItem(plexitem,triggersPresent)
        elif result == 'No results':
            updatePlexItem(plexitem,'Unknown')
        elif len(triggersPresent) == 0:
            updatePlexItem(plexitem,'Safe')
    
    else:
        pass
    #TODO ADD notice to plex showing failure to obtain value
# database = sqlite3.connect('plex_dog.db')

# Test query, remove
# dtDD = queryDTDD(triggerIDList,'Alicsadase, Darling')
# print(dtDD)

# Test Plex request, remove
headers = {
  'Accept': 'application/json',
  'X-Plex-Token': PLEX_KEY
  }
""" Fields
RatingKey - Cannot be changed
audienceRating - INT No limit on input though?
contentRating - STR (with spaces and emoji lol) No new lines, no char limits but will run off screen.
audienceRatingImage - Cannot be changed
summary - STR - Test
"""

# Get library list
libraryDetails = {}
libraries = 'library/sections'
libraryList = json.loads(requests.get(PLEX_URL + libraries, headers=headers).content)
print(libraries)
for value in libraryList['MediaContainer']['Directory']:
    if value['type'] != 'artist':
        libraryDetails[value['key']] = {
            'libraryTitle': value['title'],
            'libraryType': value['type']
          }
""" MediaLibraryTypes
movie - Movies (DTDD_ID=15)
show - TV Show (DTDD_ID=)
artist - Audio media (podcasts, music, etc) Ignore
"""

# Get media list
mediaList = {}
for libID in libraryDetails: 
    if str(libID) not in excludedLibraries:
        libraryItems = requests.get(PLEX_URL + 'library/sections/' + libID + '/all' ,headers=headers)
    else:
        print('skipping excluded library')
        continue
    if libraryItems.status_code == 200:
        itemJSON = json.loads(libraryItems.content)['MediaContainer']['Metadata']
        # Check each item in media list
    else:
        print('failed to get library')
        continue
    for itemID in itemJSON:
        item = json.loads(requests.get(PLEX_URL + 'library/metadata/' + itemID['ratingKey'] ,headers=headers).content)['MediaContainer']['Metadata'][0]
        itemGUIDs = item['Guid']

        # Extract GUID Tags for matching later
        guidDict = {}
        trackID = ''
        for ids in item['Guid']:
            guidDict[ids['id'].split('://')[0]] = ids['id'].split('://')[1]
        mediaList[item['ratingKey']] = {
            'libraryID': libID,
            'itemID': item['ratingKey'],
            'GUID': item['guid'],
            'title': item['title'],
            'releaseYear': item['year'],
            'mediaTypeTrue': item['type'],
            'dbIDs': guidDict,
        }
        dtDDInfo = mediaCheck(mediaList[item['ratingKey']])

for x in mediaList:
    print(x)



print('a')
""" MediaItems guide
ratingKey = Track item
key = link to items metadata(?)
guid = 
studio = 
type = Media type (for comedy specials will be movie)
title = Item title
summary = summary text
"""
print('aaa')
