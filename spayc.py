import json
import sys
from multiprocessing import Process, Queue

#pip install requests
import requests

import config
from utils import p, send
from serve import Serve
 
games = {}
def main():
    global p
    p(send)
    conv_auth = requests.AuthObject(config.username, config.password)

    def req(params={}):
        return requests.get('https://convore.com/api/live.json', params=params, auth=conv_auth)

    cursor = None
    while 1:
        try:
            p('requesting')
            r = req({'cursor': cursor}) if cursor else req()

            if r.status_code != 200:
                p("Got invalid status code %s on response body %s" % (r.status_code, r.content))
                continue

            response = json.loads(r.content)
            for message in response['messages']:
                cursor = message['_id']

                #ignore messages sent by ourselves to (try and) avoid infinite loops
                if message['user']['username'] == config.username:
                    continue

                if message['kind'] == 'message':
                    topic_id = message['topic']['id']
                    if topic_id in games:
                        p("forwarding message to topic_id %s" % topic_id)
                        games[topic_id][1].put(message)

                #if a new topic is created, launch a serving proces
                if message['kind'] == 'topic':
                    topic_id = message["id"]

                    queue = Queue()
                    proc = Process(target=Serve(topic_id, queue).serve)
                    proc.start()

                    games[topic_id] = (proc, queue)

                    p("created a process to serve topic_id %s" % topic_id)

                #don't print login, logout, or read messages. Eventually TODO: DELETEME
                if message['kind'] not in ['login', 'logout', 'read']:
                    p(message)

        except KeyboardInterrupt:
            sys.exit(0)


if __name__=="__main__":
    main()
