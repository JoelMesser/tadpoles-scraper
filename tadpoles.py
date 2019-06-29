import argparse
import time
import sys
import json
from gatedScraper import GatedScraper

def parentScrape(response):
    htmlResponse = response.read().decode("utf-8")
    print(htmlResponse)
    tmpSplit = htmlResponse.splitlines()
    tadpolesParams = None
    for item in tmpSplit:
        if item.strip().startswith('tadpoles.appParams'):
            tadpolesParams = item.strip()[20:-1]
    print(tadpolesParams)
    tadpolesJson = json.loads(tadpolesParams)
    startTime = tadpolesJson['first_event_time']
    endTime = tadpolesJson['last_event_time']
    children = {}
    for kid in tadpolesJson['children']:
        print(kid['display_name'])
        children[kid['key']] = kid['display_name']

    print("Start Time: " + str(startTime))
    print("End Time: " + str(endTime))
    print("For kids: " + json.dumps(children))

BASE_URL = 'https://www.tadpoles.com'

def main_loop():
    while 1:
        # do your stuff...
        time.sleep(0.1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and retrieve photos from Tadpoles.')
    parser.add_argument('--cookie', metavar='cookie', type=str, required=True,
                   help='The "cookie" header')
    parser.add_argument('--uid', metavar='uid', type=str, required=True,
                   help='The "x-tadpoles-uid" header')

    args = parser.parse_args()

    scraper = GatedScraper(cookie=args.cookie, uid=args.uid)

    scraper.add_job('/'.join([BASE_URL, 'parents']), parentScrape)

    try:
        main_loop()
    except KeyboardInterrupt:
        print >> sys.stderr, '\nExiting by user request.\n'
        sys.exit(0)
