import sys
import sqlite3

import requests

import config

def p(msg):
    print msg
    sys.stdout.flush()

db = sqlite3.connect("go.db")
def query(sql, *params):
    c = db.cursor()
    c.execute(sql, params)
    rows = c.fetchall()
    c.close()
    db.commit()
    return rows

def send(topic_id, message, **params):
    """Send a message in a thread-safe manner"""
    p("trying to send: %s to %s" % (message, topic_id))
    #does this make a request?
    conv_auth = requests.AuthObject(config.username, config.password)
    r = requests.post("https://convore.com/api/topics/%s/messages/create.json" % topic_id,
                      data={"message": message.encode('utf-8')}.update(params), auth=conv_auth)

    assert r.status_code == 200
    p("successful send")

