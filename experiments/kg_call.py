"""Example of Python client calling Knowledge Graph Search API."""
from __future__ import print_function
import json
import urllib

api_key = open('../.api_key').read()
query = 'Table Wine'
service_url = 'https://kgsearch.googleapis.com/v1/entities:search'
params = {
    'query': query,
    'limit': 10,
    'indent': True,
    'key': api_key,
}
url = service_url + '?' + urllib.parse.urlencode(params)
response = json.loads(urllib.request.urlopen(url).read())
for element in response['itemListElement']:
  print(element['result']['name'] + ' (' + str(element['resultScore']) + ')')

