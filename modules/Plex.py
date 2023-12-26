import requests
import urllib.parse
import json
import os
import emoji
import sqlite3
import re
from DTDD import dtddSearch

DTDD_QUERY_URL = 'https://www.doesthedogdie.com/dddsearch?q='
DTDD_ID_URL = 'https://www.doesthedogdie.com/media/'
DTDD_KEY = os.getenv('DTDD_KEY')
PLEX_URL = os.getenv('PLEX_URL') + ":32400/"
PLEX_KEY = os.getenv('PLEX_KEY')

excludedLibraries = ['10','13','14','4']
triggerIDWarn = [201,326]
TriggerIDAlert = [182,292]
triggerIDList = triggerIDWarn + TriggerIDAlert


    


def triggerString(IDs):
    # Create formatted trigger string
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


def updatePlexItem(mediaDetails,TriggerIDs):
    if TriggerIDs == 'Unknown':
        ValueString = emoji.emojize('? NO DATA ?')
    elif TriggerIDs == 'Safe':
        ValueString =  emoji.emojize(':check_mark:')
    else:
        ValueString = triggerString(TriggerIDs)
    request = f'library/sections/{mediaDetails["libraryID"]}/all?type=1&id={mediaDetails["itemID"]}&includeExternalMedia=1&contentRating.value={ValueString}'
    attemptUpdate = requests.put(PLEX_URL + request, headers=headers)
    print(attemptUpdate.status_code)


def searchMedia(plexitem):
    #Check media and compare search results with original file. Return info based on confidence level.
    searchResult = dtddSearch(plexitem['title'])
    if searchResult == 'No results': 
        return searchResult # Failed to find any item
    result = confidenceScore(plexitem,searchResult)
    try:
        resultDict = json.loads(result['stats'])['topics']
    except:
        resultDict = 'Invalid response'
    if result != 'No results' and resultDict !='Invalid response':

        safe = True
        conflict = 0
        triggersPresent = []
        detailedResult = dtddSearch(result['id'],'ID')
        for groups in detailedResult['allGroups']:
            for items in groups['topics']:
                if items['TopicId'] in triggerIDList:
                    # Split out for easier readability
                    yesSum = items['yesSum']
                    noSum = items['noSum']
                    # Tweak the trigger detection and alerting here
                    if yesSum == 0 and noSum == 0: # Unsure
                        print('No data')
                    elif (yesSum > noSum and noSum == 0) or (yesSum > noSum and yesSum/noSum > 1.5): # Trigger is present
                        triggersPresent.append(items['TopicId'])
                        safe = False
                    elif (yesSum == 0 and noSum > 0) or (noSum > yesSum) or noSum/yesSum > 1.5: #Tigger not present
                        pass
                    elif noSum/yesSum > 1 and noSum/yesSum < 1.5: # Conflicting response
                        conflict += 1
                        Safe = False
                    else:
                        print('unknown')
                    print(items['comment'])
        if len(triggersPresent) > 0:
            updatePlexItem(plexitem,triggersPresent)
        elif result == 'No results':
            updatePlexItem(plexitem,'Unknown')
        elif safe == True:
            updatePlexItem(plexitem,'Safe')
    else:
        pass

def confidenceScore(mediaItem,searchResults):
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
    confidence = 0
    # Create confidence score for results.
    # Scoring explained above
    for result in searchResults['items']:
        confidence = 0
        while confidence < 100:
            try: # Avoids error for TV shows that do not have a TMDBID
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
            if result['releaseYear'].isnumeric():
                if int(result['releaseYear']) == int(plexitem['releaseYear']):
                    confidence += 25
                # Sometimes DTDD will return 'unknown' for the year. #TODO #3 Add better failure prevention to the confidence checker
                elif int(result['releaseYear']) == int(plexitem['releaseYear'])+1 or int(result['releaseYear']) == int(plexitem['releaseYear'])-1:
                    confidence += 20
            break
        if confidence >= 80:
            return result, confidence
        # Else: Pass - Check next result item
        # Failed to find match
    return 'No results' # Only sent once all search results have been checked