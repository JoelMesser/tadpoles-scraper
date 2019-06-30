import argparse
import time
import sys
import json

from gatedScraper import GatedScraper

EVENTS = "https://www.tadpoles.com/remote/v1/events?direction=range&earliest_event_time={start_time}&latest_event_time={end_time}&num_events={num_events}&client=dashboard"

class TadpoleScraper():
    def __init__(self, cookie, uid, endTime=None):
        self.startTime = endTime
        self.endTime = None
        self.children = {}
        self.scraper = GatedScraper(cookie=args.cookie, uid=args.uid)
        self.scraper.add_job('/'.join([BASE_URL, 'parents']), self.parentScrape)

    def parentScrape(response):
        htmlResponse = response.read().decode("utf-8")
        tmpSplit = htmlResponse.splitlines()
        tadpolesParams = None
        for item in tmpSplit:
            if item.strip().startswith('tadpoles.appParams'):
                tadpolesParams = item.strip()[20:-1]
        print(tadpolesParams)
        tadpolesJson = json.loads(tadpolesParams)
        if self.startTime == None:
            self.startTime = tadpolesJson['first_event_time']
        self.endTime = tadpolesJson['last_event_time']
        for kid in tadpolesJson['children']:
            self.children[kid['key']] = kid['display_name']

        self.scraper.add_job(EVENTS % { start_time: self.startTime, end_time: self.endTime, num_events: 300 }, self.parseEvents)

    def parseEvents(self, response):
        txtResponse = response.read().decode("utf-8")
        jsonResponse = json.loads(txtResponse)

        jsonResponse

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
