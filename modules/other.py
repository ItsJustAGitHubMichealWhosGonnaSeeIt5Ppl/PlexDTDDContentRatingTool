""" Modules that do not fit in any of the others """
import json
import os
import emoji
import re
from datetime import datetime

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
    return tString


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
        'dtddLastUpdated':lastUpdateRE.search(item['summary']).group(1) if hasDTDD == True else False, # Only filled in if hasDTDD is True. Shows last date that information was checked for this item
        'descriptionClean':item['summary'].split('== DTDD Information ==')[0] if hasDTDD == True else item['summary'] if 'summary' in item.keys() else '', # Only filled in if hasDTDD is True.  Description without the DTDD warnings, helpful when recreating it later
        # Pre-create comment and trigger lists, makes updating them 1000x easier...
        'comments': [],
        'triggers': []
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

def triggerPlain(triggerID,triggerNames,mode=''):
    """ Convert trigger IDs to pre-defined trigger names (optional) """
    triggerID = int(triggerID)
    if triggerID in triggerNames.keys():
        return triggerNames[triggerID] if mode != 'shorten' else ''.join(x[:1] for x in triggerNames[triggerID].split(' '))# TODO #14 Allow acronym/first letter response
    else:
        return triggerID

def descriptionCreator(mediaItem,tNames={}):
    triggers = ''
    tfind = re.compile('TID\\[(.*?)\\]')
    """ Create descriptions for media items """
    for trigger in mediaItem['triggers']:
        if trigger == None:
            continue
        tName = triggerPlain(trigger,tNames)
        if isinstance(trigger,list) == True:
            tVotes = f':thumbs_up: {mediaItem["triggers"][trigger]["yes"]} / {mediaItem["triggers"][trigger]["no"]} :thumbs_down: | '
        else:
            tVotes = f''
        triggers += f'- {tVotes}{tName}\n' 
    # triggers = ('- ' + triggerPlain(trigger,tNames) for trigger in mediaItem['triggers']+ '\n')
    comments = ''.join('- ' + str(tfind.sub(triggerPlain(tfind.search(comment).group(1),tNames,'shorten'), comment) +'\n') for comment in mediaItem['comments'])
    updatedDescription = mediaItem['descriptionClean'] + f"""


== DTDD Information ==
Triggers
{triggers.strip()}
Comments
{comments}

dtddID[{mediaItem['dtddID']}]
lastUpdated[{str(datetime.now()).split(' ')[0]}]
"""
    return updatedDescription

def seriesCleaner(item):
    sDel = []
    for sID, sInf in item['seasons'].items():
        eDel= []
        if len(sInf['triggers']) == 0:
            sDel.append(sID)
            continue
        for eID, eInf in sInf['episodes'].items():
            if len(eInf['triggers']) == 0:
                eDel.append(eID)
        for eid in eDel:
            sInf['episodes'].pop(eid)
    for sid in sDel:
        item['seasons'].pop(sid)