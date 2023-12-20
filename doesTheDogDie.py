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

# TODO Move me to a place where I can be changed easily
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

#TODO Add TMDB API to check more information
""" Compare Order - Confidence score (update as needed) Mark anything that confidence score is below 80% No match below 65%
Confidence score rang (0 - 100)
IMDB ID - 100
TMDB ID - 100

Director - 30
Actor(s) - 30
Release Year - 25(?) (-5 if +or- 1 year)
Title - 20(?)
Genre - 25(?)



"""

def queryDTDD(triggerIDs,query):
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


database = sqlite3.connect('plex_dog.db')

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


mediaList = {}
for libID in libraryDetails: 
    if str(libID) not in ['10','13','14']:
        items = requests.get(PLEX_URL + 'library/sections/' + libID + '/all' ,headers=headers)
    else:
        print('skipping excluded library')
        continue
    if items.status_code == 200:
        itemJSON = json.loads(items.content)
    else:
        print('failed to get library')
        continue
    for item in itemJSON['MediaContainer']['Metadata']:
        print(item)
        
        try:
            imDB = item['Guid']['0']['id'].replace('imdb://tt','')
        except:
            imDB = 'no ID'
            pass
        
        mediaList[item['ratingKey']] = {
            'libraryID': libID,
            'GUID': item['guid'],
            'title': item['title'],
            'mediaTypeTrue': item['type'],
            'imDB': imDB,
            'triggerIDs':''
        }




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
