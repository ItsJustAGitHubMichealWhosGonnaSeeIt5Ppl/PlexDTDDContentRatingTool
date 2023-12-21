import requests
import urllib.parse
import json
import os
import emoji
import sqlite3
# Will need DB for the following
## Media Libraries
### ID / Library Name / Library Type / DTDD Relevant tag
## Media
### Media Name / Media ID / DTDD ID / Media Type ID 

DTDD_QUERY_URL = 'https://www.doesthedogdie.com/dddsearch?q='
DTDD_KEY = os.getenv('DTDD_KEY')
PLEX_URL = os.getenv('PLEX_URL') + ":32400/"
PLEX_KEY = os.getenv('PLEX_KEY')

# TODO #1 Move me to a place where I can be changed easily
excludedLibraries = [10,13,14]
triggerIDList = [182,201,292,299,320,326]


""" Trigger List (clean up later) - I DID NOT RANK THESE THIS IS THE TOPIC IDS FROM DTDD
TopicId = Topic Name < Key
    182 = Sexual Assualt (Onscreen?)
    201 = Vomitting
    292 = Rape Onscreen
    299 = Drugged
    320 = Pedo
    326 = Rape Mentioned
"""

#TODO #2 Add TMDB API to check more information


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
    # Compare items, create confidence score
    for result in dtddResults['items']:
        
        confidence = 0
        if result['name'].lower() == plexitem['title'].lower():
            confidence +=20
        try:
          if result['genre'].lower() in plexitem['Genre'].lower():
              confidence +=25
        except:
            confidence +=0
        try: # Sometimes DTDD will return 'unknown' for the year. #TODO #3 Add better failure prevention to the confidence checker
          confidence += 25 if int(result['releaseYear']) == int(plexitem['year']) else 20 if int(result['releaseYear']) == int(plexitem['year'])+1 or int(result['releaseYear']) == int(plexitem['year'])-1 else 0
        except:
            confidence +=0
        if confidence > 40 and len(result['stats']) > 4:
            resultDict = json.loads(result['stats'])['topics']
            for triggerID, triggerValue in resultDict.items():
                if int(triggerID) in triggerIDList:
                    if triggerValue["definitelyYes"] >= 1:  
                      print(f'result for {plexitem["title"]}(confidence {confidence})\nTrigger ID: {triggerID}\n- - Not present: {triggerValue["definitelyNo"]}\n- - Present: {triggerValue["definitelyYes"]}')
                


# database = sqlite3.connect('plex_dog.db')

# Test query, remove
# dtDD = queryDTDD(triggerIDList,'Alicsadase, Darling')
# print(dtDD)

# Test Plex request, remove
headers = {
  'Accept': 'application/json',
  'X-Plex-Token': PLEX_KEY
  }

response = requests.get(PLEX_URL + 'library/metadata/2', headers=headers)
movieDetails = json.loads(response.content)

libID = 1 # Movie library
movieID = 2 # 22 Jump Street, testing
updateFieldName = 'audienceRating'
updateValue = 102
request = f'library/sections/{libID}/all?type=1&id={movieID}&includeExternalMedia=1&{updateFieldName}.value={updateValue}'
attemptUpdate = requests.put(PLEX_URL + request, headers=headers)
print(attemptUpdate)


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
    if str(libID) not in ['10','13','14','4']:
        items = requests.get(PLEX_URL + 'library/sections/' + libID + '/all' ,headers=headers)
    else:
        print('skipping excluded library')
        continue
    if items.status_code == 200:
        itemJSON = json.loads(items.content)
        # Check each item in media list
    else:
        print('failed to get library')
        continue
    for item in itemJSON['MediaContainer']['Metadata']:
        dtDDInfo = mediaCheck(item)

        # Attempt to add IMDB Tag
        try:
            imDB = item['Guid']['0']['id'].replace('imdb://tt','')
            tmDB = item['Guid']['1']['id'].replace('imdb://tt','')
            idid = item['Guid']['2']['id'].replace('imdb://tt','')
        except:
            imDB = tmDB = 'no ID'
        dtDDInfo = mediaCheck(item)
        mediaList[item['ratingKey']] = {
            'libraryID': libID,
            'GUID': item['guid'],
            'title': item['title'],
            'mediaTypeTrue': item['type'],
            'imDB': imDB,
            'triggerIDs':'dtDDInfo',
            'confidence':'dtDDInfo'
            
        }

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
