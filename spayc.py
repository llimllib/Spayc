import json
import sqlite3

#pip install requests
import requests

import config

db = sqlite3.connect("go.db")
def query(sql, *params):
    c = db.cursor()
    c.execute(sql, params)
    rows = c.fetchall()
    c.close()
    db.commit()
    return rows

def help(message):
    """Look for a help request and handle it if it's found"""
    if 'help' not in hooks: return

    r = re.search(r"\/help ?([\w.\-_]+)?", message['message'])
    if not r: return

    send(message['topic']['id'], "Sorry, help isn't working yet!")

def main():
    conv_auth = requests.AuthObject(config.username, config.password)

    def req(params={}):
        return requests.get('https://convore.com/api/live.json', params=params, auth=conv_auth)

    cursor = None
    while 1:
        try:
            p('requesting')
            r = req({'cursor': cursor}) if cursor else req()
            assert r.status_code == 200, "Got invalid status code %s on response body %s" % (r.status_code, r.content)
            p(r.content)
            response = json.loads(r.content)
            for message in response['messages']:

                #ignore messages sent by ourselves to (try and) avoid infinite loops
                if message['user']['username'] == config.username:
                    continue

                if message['kind'] == 'message':
                    help(message)

                cursor = message['_id']

                #don't print login, logout, or read messages. Eventually TODO: DELETEME
                if message['kind'] not in ['login', 'logout', 'read']:
                    p(message)

        except KeyboardInterrupt:
            sys.exit(0)


if __name__=="__main__":
    main()
