"""Serve a game of go"""
import sqlite3
import json
from time import sleep
from subprocess import Popen, PIPE
from multiprocessing import Queue

import requests

import config
from utils import send, p, query

class GnugoException(Exception): pass

class Gnugo(object):
    def __init__(self):
        self.gnugo = Popen("gnugo --mode gtp", shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True, bufsize=1) 
        #command id
        self.cid = 1

    def command(self, command, *args):
        strargs = " ".join(map(str, args))
        self.gnugo.stdin.write("%s %s %s\n" % (self.cid, command, strargs))

        #TODO: validate the return value?
        #the return begins with an = on success, fail on failure
        line = self.gnugo.stdout.readline()

        response = [line]
        while line != "\n":
            line = self.gnugo.stdout.readline()
            response.append(line)

        response = "".join(response)

        if not response.startswith("="):
            raise GnugoException(response)

        return response

class Serve(object):
    def __init__(self, topic_id, queue):
        self.topic_id = topic_id
        self.message_queue = queue 

        #don't start a gnugo unless the user wants a game
        self.gnugo = None

    def send(self, msg, **params):
        send(self.topic_id, msg, **params)

    def showboard(self):
        board = self.gnugo.command("showboard")
        #return all but the first and last lines
        self.send("\n".join(board.split("\n")[1:-1]), pasted=True)

    def get_computer_move(self, color):
        def _get_computer_move(self):
            move = self.gnugo.command("genmove", color)
            self.send("black played %s" % move)
        return _get_computer_move(self)

    def get_human_move(self, color):
        def _get_human_move(self):
            msg = self.get_legal_move(color)
            self.gnugo.command("play", color, msg)
        return _get_human_move(self)

    def legalmove(self, color, msg):
        p("checking color %s msg %s" % (color, msg))
        try:
            r = self.gnugo.command("is_legal", color, msg)
            isvalid = r.split(" ")[1][0] == '1'
            p("Is Legal? %s %s %s" % (isvalid, r, r.split(" ")))
            return isvalid
        except GnugoException as e:
            p("Got a gnugo exception: %s" % e)
            #TODO: print a nice error to the user
            return False

    def get_int(self, prompt, min_, max_, default):
        self.send(prompt)
        msg = self.message_queue.get()

        try:
            sz = int(msg["message"])
            if not min_ <= sz <= max_: sz = default
        except ValueError:
            sz = default

        return sz

    def get_move_or_pass(self):
        self.send("Enter coordinates to make a move, or type 'pass' to play white:")
        msg = self.message_queue.get()

        while not (msg['message'] == "pass" or self.legalmove("black", msg["message"])):
            self.send("invalid move. Try again:")
            msg = self.message_queue.get()

        return msg

    def get_legal_move(self, color):
        self.send("Enter the coordinates of your move:")
        msg = self.message_queue.get()

        while not self.legalmove(color, msg["message"]):
            self.send("Invalid move. Enter the coordinates of your move:")
            msg = self.message_queue.get()

        return msg

    def serve_game(self, topic_id):
        p("serving game!")

        self.gnugo = Gnugo()

        sz = self.get_int("What boardsize would you like? (19):", 9, 19, 19)
        self.gnugo.command("boardsize", sz)

        handicap = self.get_int("What handicap would you like? (0):", 0, 12, 0)
        if handicap > 0:
            self.gnugo.command("fixed_handicap", handicap)

        self.showboard()

        if handicap == 0:
            msg = self.get_move_or_pass()
        else:
            msg = self.get_legal_move("black")

        if msg["message"] == "pass":
            move = self.gnugo.command("genmove black")
            self.send("Black played %s" % move)
            black, white = self.get_computer_move("black"), self.get_human_move("white")
        else:
            self.gnugo.command("play black %s" % msg["message"])
            white, black = self.get_computer_move("white"), self.get_human_move("black")

        self.showboard()

        #each run through this loop handles a (white, black) move pair
        while 1:
            black()
            self.showboard()
            white()
            self.showboard()

    def serve(self):
        #avoid the "new room quick message" bug
        sleep(.37)

        self.send("Would you like to play a game of go (Y/n)?")

        msg = self.message_queue.get()

        if msg['message'] == "n":
            self.send("Ok, I'll leave you alone then!")
        else:
            self.serve_game(self.topic_id)
