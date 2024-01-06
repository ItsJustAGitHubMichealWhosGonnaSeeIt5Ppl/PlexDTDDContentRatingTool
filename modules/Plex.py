import requests
import urllib.parse
import json
import os
import emoji
import sqlite3
import re
from .other import mediaDictCreator
#from .DTDD import dtddSearch, dtddComments


DTDD_QUERY_URL = 'https://www.doesthedogdie.com/dddsearch?q='
DTDD_ID_URL = 'https://www.doesthedogdie.com/media/'
DTDD_KEY = os.getenv('DTDD_KEY')
PLEX_URL = os.getenv('PLEX_URL') + ":32400/"
PLEX_KEY = os.getenv('PLEX_KEY')

excludedLibraries = ['10','13','14','4']
triggerIDWarn = [201,326]
TriggerIDAlert = [182,292]
triggerIDList = triggerIDWarn + TriggerIDAlert
plexHeader = {
  'Accept': 'application/json',
  'X-Plex-Token': PLEX_KEY
  }


def updatePlexItem(mediaType,mediaDetails,TriggerString,Description):
    """ Update a plex media library item """
    # TODO #5 Allow any field to be updated by accepting a table.
    request = f'library/sections/{mediaDetails["libraryID"]}/all?type={1 if mediaType == "movie" else 4}&id={mediaDetails["itemID"]}&includeExternalMedia=1&contentRating.value={TriggerString}'
    attemptUpdate = requests.put(PLEX_URL + request, headers=plexHeader)
    print(attemptUpdate.status_code)



def getPlexItem(getType,ID=None,raw=False):
    """ Get plex library items.
    if raw = True, the raw response will be returned,
    ### getTypes
    libraries - List of libraries 
    libraryItems - List of library items (requires ID field)
    LibraryItem - Single library item (requires ID field)
    """
    getType = getType.lower() # cleanup input.
    types = {
    'libraries': 'library/sections',
    'libraryitems': None if getType != 'libraryitems' else f'library/sections/{ID}/all', # avoids error if no ID is provided
    'libraryitem': None if getType != 'libraryitem' else f'library/metadata/{ID}', # avoids error if no ID is provided
    }
    if getType not in types.keys():
        return 'invalid getType'
    if getType != 'libraries' and ID == None:
        return f'ID required for getType {getType}'
    
    request = requests.get(PLEX_URL + types[getType], headers=plexHeader)
    if request.status_code == 200: # Confirm response is valid
        #TODO #6 Make response validation function
        response = json.loads(request.content)
    else:
        return f'request failed - {request.status_code}'
    if raw == True:
        return response
    
    # Format responses
    if getType == 'libraries':
        formattedResponse = {}
        for value in response['MediaContainer']['Directory']:
            if value['type'] != 'artist':
                formattedResponse[value['key']] = {
                    'libraryTitle': value['title'],
                    'libraryType': value['type']
                }
    elif getType == 'libraryitems':
        formattedResponse = response['MediaContainer']['Metadata']
    elif getType == 'libraryitem': # Probably a nicer way to do this
        formattedResponse = response['MediaContainer']['Metadata'][0] 
    else:
        return 'Invalid getType, this error should never appear...'
    return formattedResponse # Returns formatted resposne here rather than inline in case more items need to be added later.



def getPlexTV(showID):
    """ Get entire TV show information (all episodes) """
    
    seasonDict = {}
    showRequest = requests.get(PLEX_URL + 'library/metadata/' + showID + '/children' ,headers=plexHeader)
    
    # TVShowSeasons = json.loads(requests.get(PLEX_URL + 'library/metadata/' + showID + '/children' ,headers=plexHeader).content)
    if showRequest.status_code != 200:
        return 'Failed to get show'
    else:
        seasons = json.loads(showRequest.content)
    for season in seasons['MediaContainer']['Metadata']:
        episodeDict = {}
        episodeDictTest = {}
        seasonRequest = requests.get(PLEX_URL + 'library/metadata/' + season['ratingKey'] + '/children' ,headers=plexHeader)# Get season episodes
        if seasonRequest.status_code != 200:
            return 'Failed to get episodes'
        else:
            episodes = json.loads(seasonRequest.content)
            
        for episode in episodes['MediaContainer']['Metadata']:
            print(f'{season["parentTitle"]} - S{season["index"]}E{episode["index"]}')
            episdodeDetails = getPlexItem('libraryitem',episode['ratingKey'])
            episodeDict[episode['index']] = mediaDictCreator(episdodeDetails,'tvEpisode')
        
        seasonDict[season['index']] = mediaDictCreator(season,'tvSeason',MDCepisodes=episodeDict)
    return seasonDict

    


def plexQuickGrab():
    """ Get all items from all libraries """
    
    
    
    
    
    
