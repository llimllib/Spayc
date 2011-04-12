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

    conv_auth = requests.AuthObject(config.username, config.password)

    data = {"message": message.encode('utf-8')}
    data.update(params)

    r = requests.post("https://convore.com/api/topics/%s/messages/create.json" % topic_id,
                      data=data, auth=conv_auth)

    assert r.status_code == 200
    p("successful send")

