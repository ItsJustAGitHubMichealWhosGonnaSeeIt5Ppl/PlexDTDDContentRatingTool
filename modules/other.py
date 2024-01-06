""" Modules that do not fit in any of the others """
import requests
import urllib.parse
import json
import os
import emoji
import sqlite3
import re
from .DTDD import dtddSearch, dtddComments

DTDD_QUERY_URL = 'https://www.doesthedogdie.com/dddsearch?q='
DTDD_ID_URL = 'https://www.doesthedogdie.com/media/'
DTDD_KEY = os.getenv('DTDD_KEY')
PLEX_URL = os.getenv('PLEX_URL') + ":32400/"
PLEX_KEY = os.getenv('PLEX_KEY')

def triggerString(presentIDs,alertList,warnList):
    """ Returns a trigger string for media items. 
    NOTE: This version is built for specific people, hence the M and E.
    
    Later versions will make this generic
    TODO: #4 Make triggerString more generic
    
    """
    # Create formatted trigger string
    eWarn = warn = alert = False
    tString = ''
    for ID in presentIDs:
        if int(ID) in warnList:
            if int(ID) == 201:
                eWarn = True # Extra warning for single user 
            else:
                warn = True
        if int(ID) in alertList:
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



def showTriggerIndexer(showID,dtddID,triggerID,showDict):
    """ Index TV show episodes for updating individual episode triggers once all triggers have been checked
    
    Season = index1
    Episode = index2 
    """
    plexHeader = {
    'Accept': 'application/json',
    'X-Plex-Token': PLEX_KEY
    }
    comments = dtddComments(dtddID,triggerID)
    for comment in comments:
        if comment['yes'] > comment['no']: # Verify comment is not downvoted.
            tv = requests.get(PLEX_URL + 'library/metadata/' + showID + '/children' ,headers=plexHeader)
            TVShowSeasons = json.loads(tv.content)
            # TVShowSeasons = json.loads(requests.get(PLEX_URL + 'library/metadata/' + showID + '/children' ,headers=plexHeader).content)
            for seasonPlex in TVShowSeasons['MediaContainer']['Metadata']:
                if int(seasonPlex['index']) == int(comment['index1']): # Find correct season
                    TVShowEpisodes = json.loads(requests.get(PLEX_URL + 'library/metadata/' + seasonPlex['ratingKey'] + '/children' ,headers=plexHeader).content) # Get season episodes
                    for episodePlex in TVShowEpisodes['MediaContainer']['Metadata']: 
                        if int(episodePlex['index']) == int(comment['index2']): # Find correct episode
                            showDict.update({episodePlex["ratingKey"]: {
                                'triggerIDs': showDict[episodePlex["ratingKey"]]['triggerIDs'].append(triggerID) if episodePlex["ratingKey"] in showDict else [triggerID],
                                'comments': showDict[episodePlex["ratingKey"]]['comments'].append(comment['comment']) if episodePlex["ratingKey"] in showDict else [comment['comment']],
                            }})
                            break                
                            


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
                if int(result['releaseYear']) == int(mediaItem['releaseYear']):
                    confidence += 25
                # Sometimes DTDD will return 'unknown' for the year. #TODO #3 Add better failure prevention to the confidence checker
                elif int(result['releaseYear']) == int(mediaItem['releaseYear'])+1 or int(result['releaseYear']) == int(mediaItem['releaseYear'])-1:
                    confidence += 20
            break
        if confidence >= 80:
            return result, confidence
        # Else: Pass - Check next result item
        # Failed to find match
    return 'No results' # Only sent once all search results have been checked



def mediaDictCreator(item,mode,**extras):
    """ Create media dictionary items 
    ### Modes
    - default - Default mode, contains all fields
    - single -
    - tvSeries - TV Series Mode
    - tvSeason - TV Season Mode
    - tvEpisode - TV Episode Mode
    """
    def argCheck(name,item=None):
        if item == None:
            item = extras
        """ Checks for item in **extras"""
        return item[name] if name in item.keys() else None
    # Common across all types of request
    common = {
        'itemID': item['ratingKey'],
        'title': item['title'],
        'description':item['summary'] if 'summary' in item.keys() else '',   
    }
    
    # DTDD dict items
    # Regex queries to be used when finding media information.
    dtddRE = re.compile('dtddID\\[(.*?)\\]')
    lastUpdateRE = re.compile('lastUpdated\\[(.*?)\\]')
    hasDTDD = True if '== DTDD Information ==' in (item['summary'] if 'summary' in item.keys() else '') else False
    dtdd = {
        'hasDTDD': hasDTDD, # True/False.
        'dtddID':dtddRE.search(item['summary']).group(1) if hasDTDD == True else False, # Only filled in if hasDTDD is True. 
        'dtddLastChecked':lastUpdateRE.search(item['summary']).group(1) if hasDTDD == True else False, # Only filled in if hasDTDD is True. Shows last date that information was checked for this item
        'descriptionClean':item['summary'].split('== DTDD Information ==') if hasDTDD == True else False # Only filled in if hasDTDD is True.  Description without the DTDD warnings, helpful when recreating it later
    }
    
    # Mode Dependant Items
    
    if mode.lower() == 'default':
        additionalItems = {
            'libraryID': argCheck('libID'),
            'itemType': argCheck('libInf'),
            'GUID': item['guid'],
            'releaseYear': item['year'],
            'mediaTypeTrue': item['type'],
            'dbIDs': argCheck('gDict'), # Helps when matching media 
        }
    elif mode.lower() == 'tvseries':
        additionalItems = {'seasons': argCheck('seasonsDict')}
    elif mode.lower() == 'tvseason':
        additionalItems = {'episodes': argCheck('MDCepisodes')}
    else:
        additionalItems = {}
    return common | additionalItems | dtdd
    ### I had never heard of "|" before this project. Thanks to the following articles
    # https://stackoverflow.com/questions/38987/how-do-i-merge-two-dictionaries-in-a-single-expression-in-python
    # https://datagy.io/python-merge-dictionaries/



def trashMatch(queryKey,dataToSearch): 
    """ match dictionary subitems in a trash way """
    for data in dataToSearch:
        if queryKey == data:
            return data
    


def dictMatch(source, **searchItem): 
    """ match dictionary subitems """
    