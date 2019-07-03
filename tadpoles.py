import argparse
import time
import sys
import json
from datetime import date

from gatedScraper import GatedScraper

EVENTS = "https://www.tadpoles.com/remote/v1/events?direction=range&earliest_event_time={start_time}&latest_event_time={end_time}&num_events={num_events}&client=dashboard"
ATTACHMENT = "https://www.tadpoles.com/remote/v1/obj_attachment?obj={obj}&key={key}"

class TadpoleScraper():
    def __init__(self, cookie, uid, endTime=None):
        self.startTime = endTime
        self.endTime = None

        self.minTime = 10000000000
        self.maxTime = 0

        self.children = {}
        self.attachments = {}
        self.scraper = GatedScraper(cookie=args.cookie, uid=args.uid, interval=5)
        self.scraper.add_job('/'.join([BASE_URL, 'parents']), self.parentScrape)

    def parentScrape(self, response, otherParams):
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

        print("Started at Goddard: " + str(date.fromtimestamp(self.startTime)))
        print("Last event at Goddard: " + str(date.fromtimestamp(self.endTime)))

        self.addEventJob(self.startTime, self.endTime)

    def addEventJob(self, incStart, incEnd):
        duration = min(incEnd - incStart, 2592000 * 2)
        newEnd = min(incStart + duration, incEnd)
        print("Adding request from : " + str(date.fromtimestamp(incStart)) + " to " + str(date.fromtimestamp(newEnd)))
        self.scraper.add_job(EVENTS.format(start_time=incStart, end_time=newEnd, num_events=300), self.parseEvents, start_time=incStart, end_time=newEnd)

    def processAttachments(self):
        print("Start: " + str(date.fromtimestamp(self.minTime)))
        print("Stop: " + str(date.fromtimestamp(self.maxTime)))
        print(str(len(self.attachments)) + " attachments to parse")
        def sortMethod(val):
            return val['create_time']
        attachVals = self.attachments.values()
        attachVals.sort(sortMethod)
        for singleAttach in attachVals:
            self.scraper.add_job(ATTACHMENT.format(key=singleAttach['attachment'], obj=singleAttach['key']), self.processImage, child=singleAttach['child'], create_time=singleAttach['create_time'], comment=singleAttach['comment'])
            break

    def processImage(self, response, otherParams):
        data = response.read()
        with open("")

    def parseEvents(self, response, otherParams):
        print("Parse Events")
        txtResponse = response.read().decode("utf-8")
        jsonResponse = json.loads(txtResponse)

        print(otherParams)
        if otherParams['start_time'] >= otherParams['end_time']:
            self.processAttachments()
            return
        
        last_time = otherParams['end_time']
        for singleEvent in jsonResponse['events']:
            last_time = max(last_time, singleEvent['create_time'])
            self.maxTime = max(self.maxTime, singleEvent['create_time'])
            self.minTime = min(self.minTime, singleEvent['create_time'])
            # if the event has an attachment, push it
            if 'attachments' in singleEvent:
                for singleAttach in singleEvent['attachments']:
                    toPush = {}
                    toPush['attachment'] = singleAttach
                    toPush['key'] = singleEvent['key']
                    toPush['child'] = singleEvent['parent_member_display']
                    toPush['create_time'] = singleEvent['create_time']
                    toPush['comment'] = None
                    self.attachments[singleAttach] = toPush
            
            # If the event has entries, check them
            if 'entries' in singleEvent:
                for singleEntry in singleEvent['entries']:
                    if 'attachment' in singleEntry:
                        tmpKey = singleEntry['attachment']['key']
                        toPush = {}
                        toPush['attachment'] = tmpKey
                        toPush['key'] = singleEvent['key']
                        toPush['child'] = singleEvent['parent_member_display']
                        toPush['create_time'] = singleEvent['create_time']
                        if 'note' in singleEntry:
                            toPush['comment'] = singleEntry['note']
                        self.attachments[tmpKey] = toPush

        print("Add Another Event")
        #Push event onto stack.
        if last_time > self.endTime:
            self.processAttachments()
        else:
            self.addEventJob(last_time, self.endTime)
                

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

    scraper = TadpoleScraper(cookie=args.cookie, uid=args.uid)

    try:
        main_loop()
    except KeyboardInterrupt:
        print >> sys.stderr, '\nExiting by user request.\n'
        sys.exit(0)
