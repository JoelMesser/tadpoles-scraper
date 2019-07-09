from apscheduler.schedulers.background import BackgroundScheduler
import urllib.request
import time

class GatedScraper:
    def __init__(self, cookie, uid, interval=15):
        if(cookie == None):
            raise Exception('Cookie is required to be set')

        if(uid == None):
            raise Exception('Tadpoles UID is required to be set')

        self.cookie = cookie
        self.uid = uid
        self.requests = []

        self.sched = BackgroundScheduler()
        self.sched.start()
        self.sched.add_job(self.fire_job, 'interval', seconds=interval, jitter=5)

    def fire_job(self):
        if(len(self.requests) == 0):
            return
        
        currentItem = self.requests.pop(0)

        if currentItem['url'] == None:
            currentItem['callback'](None, currentItem['params'])
            return

        curReq = urllib.request.Request(currentItem['url'])
        curReq.add_header('cookie', self.cookie)
        curReq.add_header('x-tadpoles-uid', self.uid)
        resp = urllib.request.urlopen(curReq)
        if(resp.getcode() >= 300):
            self.requests.insert(0, currentItem)
            self.sched.pause()
            time.sleep(10)
            self.sched.resume()
        else:
            currentItem['callback'](resp, currentItem['params'])

    def add_job(self, url, callback, **params):
        to_append = {}
        to_append['url'] = url
        to_append['callback'] = callback
        to_append['params'] = params
        self.requests.append(to_append)

    def pause(self):
        self.sched.pause()
    
    def start(self):
        self.sched.start()