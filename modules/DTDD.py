# Imports
import requests
import urllib.parse
import json
import os
import emoji
import sqlite3
import re

# CONSTANTS
DTDD_BASE = 'https://www.doesthedogdie.com'
DTDD_KEY = os.getenv('DTDD_KEY')
# /dddsearch?q=
# /media/

def dtddSearch(query,mode='Q'):
    """ Search the DTDD API. Default mode is query, enter literally anything else to switch it. """
    # Search by ID or text
    headers = {
    'Accept': 'application/json',
    'X-API-KEY': DTDD_KEY
    }
    subString = '/dddsearch?q=' if mode.upper() == 'Q' else '/media/'
    response = requests.get(DTDD_BASE + subString + str(query) ,headers = headers)
    if response.status_code == 200 and len(json.loads(response.content)['item']) > 0:
        return json.loads(response.content)
    else:
        return f'Failed to find item'