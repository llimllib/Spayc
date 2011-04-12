"""Serve a game of go"""
import sqlite3
import json
from subprocess import Popen, PIPE
from multiprocessing import Queue

import requests

import config
from utils import send, p, query

class Gnugo(object):
    def __init__(self):
        self.gnugo = Popen("gnugo --mode gtp", shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True, bufsize=1) 
        #command id
        self.cid = 1

    def command(self, command, *args):
        strargs = " ".join(map(str, args))
        self.gnugo.stdin.write("%s %s %s\n" % (self.cid, command, strargs))

        #TODO: validate the return value?
        line = self.gnugo.stdout.readline()
        response = [line]
        while line != "\n":
            line = self.gnugo.stdout.readline()
            response.append(line)

        return "".join(response)

class Serve(object):
    def __init__(self, topic_id, queue):
        self.topic_id = topic_id
        self.message_queue = queue 

        #don't start a gnugo unless the user wants a game
        self.gnugo = None

    def send(self, msg, **params):
        send(self.topic_id, msg, **params)

    def serve_game(self, topic_id):
        p("serving game!")

        self.gnugo = Gnugo()

        self.send("What boardsize would you like? (19):")
        msg = self.message_queue.get()
        try:
            sz = int(msg["message"])
            if not 9 < sz < 19:
                sz = 19
        except ValueError:
            sz = 19
        self.gnugo.command("boardsize", sz)

        self.send(self.gnugo.command("showboard"), paste=True)

        self.send("more of a game to come in teh future!")

    def serve(self):
        self.send("Would you like to play a game of go (Y/n)?")
        msg = self.message_queue.get()
        p("message received: %s" % msg)

        if msg['message'] == "n":
            self.send("Ok, I'll leave you alone then!")
        else:
            self.serve_game(self.topic_id)
