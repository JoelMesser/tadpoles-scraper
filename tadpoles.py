import argparse
import time
import sys
import json
import piexif
import os
import math
import logging
from progress.bar import Bar
from PIL import Image
from datetime import date
from datetime import datetime

from gatedScraper import GatedScraper

LAST_RUN_FILE = 'lastRun'
MAX_DURATION = 2592000 * 2
EVENTS = "https://www.tadpoles.com/remote/v1/events?direction=range&earliest_event_time={start_time}&latest_event_time={end_time}&num_events={num_events}&client=dashboard"
ATTACHMENT = "https://www.tadpoles.com/remote/v1/obj_attachment?obj={obj}&key={key}"

logging.getLogger('apscheduler.scheduler').setLevel(logging.CRITICAL)
logging.getLogger('apscheduler.scheduler').propagate = False


class TadpoleScraper():
    def __init__(self, cookie, uid, out, interval, lastEndTime=None):
        self.startTime = lastEndTime
        self.endTime = None
        self.outLoc = out
        self._isFinished = False

        self.minTime = 10000000000
        self.maxTime = 0

        self.children = {}
        self.attachments = {}

        self.attachmentsBar = None
        self.eventBar = None

        self.scraper = GatedScraper(cookie=args.cookie, uid=args.uid, interval=interval)
        self.scraper.add_job('/'.join([BASE_URL, 'parents']), self.parentScrape)

    def writeLastTime(self, lastTime):
        lastFileLoc = os.path.join(self.outLoc, LAST_RUN_FILE)
        with open(lastFileLoc, "w") as r:
            r.write(str(lastTime))
            r.close()

    def parentScrape(self, response, otherParams):
        htmlResponse = response.read().decode("utf-8")
        tmpSplit = htmlResponse.splitlines()
        tadpolesParams = None
        for item in tmpSplit:
            if item.strip().startswith('tadpoles.appParams'):
                tadpolesParams = item.strip()[20:-1]
        
        tadpolesJson = json.loads(tadpolesParams)
        if self.startTime == None:
            self.startTime = tadpolesJson['first_event_time']

        self.endTime = tadpolesJson['last_event_time']
        
        print("Last Downloaded: " + str(date.fromtimestamp(self.startTime)))
        print("Last event at Goddard: " + str(date.fromtimestamp(self.endTime)))

        total_events = math.ceil((self.endTime - self.startTime) / MAX_DURATION)
        if(total_events == 0):
            print("No images / videos to download")
            self.finish(None, None)
            return

        self.eventBar = Bar("Parsing Events", max=total_events, suffix='%(index)d/%(max)d - %(eta)d seconds remaining')
        
        for kid in tadpolesJson['children']:
            kidFirstName = kid['display_name'].split(' ')[0]
            if not os.path.exists(os.path.join(self.outLoc, kidFirstName)):
                os.makedirs(os.path.join(self.outLoc, kidFirstName))
            self.children[kid['key']] = kidFirstName

        self.addEventJob(self.startTime, self.endTime)

    def addEventJob(self, incStart, incEnd):
        duration = min(incEnd - incStart, MAX_DURATION)
        newEnd = min(incStart + duration, incEnd)
        self.scraper.add_job(EVENTS.format(start_time=incStart, end_time=newEnd, num_events=300), self.parseEvents, start_time=incStart, end_time=newEnd)

    def finish(self, resp, params):
        self.writeLastTime(self.endTime)
        if(self.attachmentsBar != None):
            self.attachmentsBar.finish()
        self._isFinished = True
    
    def isFinished(self):
        return self._isFinished

    def processAttachments(self):
        print('')
        self.attachmentsBar = Bar("Downloading Attachments", max=len(self.attachments), suffix='%(index)d/%(max)d - %(eta)d seconds remaining')
        def sortMethod(val):
            return val['create_time']
        attachVals = list(self.attachments.values())
        attachVals.sort(key=sortMethod)
        for singleAttach in attachVals:
            callback = self.processImage
            if(singleAttach['mime_type'] == 'video/mp4'):
                callback = self.processVideo
            self.scraper.add_job(ATTACHMENT.format(key=singleAttach['attachment'], obj=singleAttach['key']), callback, child=singleAttach['child'], create_time=singleAttach['create_time'], comment=singleAttach['comment'])
        self.scraper.add_job(None, self.finish)

    def processVideo(self, response, otherParams):
        data = response.read()
        time = datetime.fromtimestamp(otherParams['create_time'])
        timeStr = time.strftime("%Y%m%d.%H%M%S")
        fileStr = "{kid}-{time_str}.mp4".format(kid=otherParams['child'], time_str=timeStr)
        fileLoc = os.path.join(self.outLoc, otherParams['child'], fileStr)

        with open(fileLoc, "wb") as f:
            f.write(data)
            f.close()
        
        self.writeLastTime(otherParams['create_time'])
        self.attachmentsBar.next()

    def processImage(self, response, otherParams):
        data = response.read()
        time = datetime.fromtimestamp(otherParams['create_time'])
        timeStr = time.strftime("%Y%m%d.%H%M%S")
        fileStr = "{kid}-{time_str}.jpg".format(kid=otherParams['child'], time_str=timeStr)
        fileLoc = os.path.join(self.outLoc, otherParams['child'], fileStr)

        with open(fileLoc, "wb") as f:
            f.write(data)
            f.close()

        try:
            im = Image.open(fileLoc)
            exif_dict = piexif.load(im.info["exif"])
            # process im and exif_dict...
            if otherParams['comment'] != None:
                exif_dict["0th"][piexif.ImageIFD.ImageDescription] = otherParams['comment'].encode("utf8")
            exif_dict["0th"][piexif.ImageIFD.DateTime] = time.strftime("%H:%M:%S %m/%d/%Y")
            exif_bytes = piexif.dump(exif_dict)
            im.save(fileLoc, "jpeg", exif=exif_bytes)
        except Exception as e:
            print("Error " + e)
            print("Error Details: " + otherParams)
        else:
            im.close()

        self.writeLastTime(otherParams['create_time'])
        self.attachmentsBar.next()

    def parseEvents(self, response, otherParams):
        txtResponse = response.read().decode("utf-8")
        jsonResponse = json.loads(txtResponse)
        self.eventBar.next()

        if otherParams['start_time'] >= otherParams['end_time']:
            self.eventBar.finish()
            self.processAttachments()
            return
        
        last_time = otherParams['end_time']
        for singleEvent in jsonResponse['events']:
            last_time = max(last_time, singleEvent['create_time'])
            self.maxTime = max(self.maxTime, singleEvent['create_time'])
            self.minTime = min(self.minTime, singleEvent['create_time'])
            # if the event has an attachment, push it
            if 'new_attachments' in singleEvent:
                for singleAttach in singleEvent['new_attachments']:
                    toPush = {}
                    toPush['attachment'] = singleAttach['key']
                    toPush['key'] = singleEvent['key']
                    toPush['child'] = singleEvent['parent_member_display']
                    toPush['create_time'] = singleEvent['create_time']
                    toPush['mime_type'] = singleAttach['mime_type']
                    toPush['comment'] = None
                    self.attachments[singleAttach['key']] = toPush
            
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
                        toPush['mime_type'] = singleEntry['attachment']['mime_type']
                        toPush['comment'] = None
                        if 'note' in singleEntry:
                            toPush['comment'] = singleEntry['note']
                        
                        self.attachments[tmpKey] = toPush

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
    parser.add_argument('--out', metavar='out', type=str,
                    help='The output location')
    parser.add_argument('--interval', metavar='interval', type=int, default=5,
                    help='Time between requests')

    args = parser.parse_args()
    outLoc = args.out
    if outLoc == None:
        outLoc = os.getcwd()

    if not os.path.exists(outLoc):
        os.makedirs(outLoc)
    
    print("Starting up, grabbing initial parameters.")

    lastFileLoc = os.path.join(outLoc, LAST_RUN_FILE)
    lastTime = None
    if os.path.exists(lastFileLoc):
        with open(lastFileLoc, "r") as r:
            lastTime = float(r.read())
            r.close()

    scraper = TadpoleScraper(cookie=args.cookie, uid=args.uid, out=outLoc, interval=args.interval, lastEndTime=lastTime)

    while not scraper.isFinished():
        # do your stuff...
        time.sleep(1.0)
