"""Serve a game of Go to a convore topic"""
from time import sleep

import requests

from utils import send, p, query
from gnugo import Gnugo, GnugoException

class Gogame(object):
    HUMAN = 0
    COMPUTER = 1

    ACTIVE = 0
    PASS = 1
    FINISHED = 2

    def __init__(self, topic_id, queue):
        self.topic_id = topic_id
        self.message_queue = queue 

        #don't start a gnugo unless the user wants a game
        self.gnugo = None

        self.black = Serve.HUMAN
        self.white = Serve.COMPUTER 

        self.gamestate = Serve.ACTIVE

    def send(self, msg, **params):
        send(self.topic_id, msg, **params)

    def showboard(self):
        board = self.gnugo.command("showboard")
        #return all but the first and last lines
        self.send("\n".join(board.split("\n")[1:-1]), pasted=True)

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

    def help(self, msg):
        self.send("""Moves are specified as <letter><number> pairs without spaces in between them,
        like 'C4' or 'E10'.
        
        Type /raw <command> to enter a raw GTP command for debugging
        
        Please report bugs to bill.mill@gmail.com""")

    def raw_cmd(self, msg):
        msg = " ".join(msg.split(" ")[1:])
        try:
            self.send(self.gnugo.command(msg), pasted=True)
        except GnugoException as e:
            self.send(e.message, pasted=True)

    def get_human_move(self, color):
        commands = {
            "help": self.help,
            "/raw": self.raw_cmd,
        }

        #pull messages until we get a valid command for @color
        while 1:
            self.send("Enter a legal move for %s:" % color)

            msg = self.message_queue.get()
            m = msg['message']
            cmd = m.split(" ")[0]

            if self.legalmove(color, m):
                self.gnugo.command("play", color, m)
                if m.lower() == "pass":
                    if self.gamestate == Serve.PASS:
                        self.gamestate = Serve.FINISHED
                    else:
                        self.gamestate = Serve.PASS
                else:
                    self.showboard()
                break
            elif cmd in commands:
                commands[cmd](m)

            p("didn't find command %s" % (cmd))

    def get_computer_move(self, color):
        mv = self.gnugo.command("genmove", color).split()[1]
        self.send("%s played %s" % (color, mv))

        if mv.lower() == "pass":
            if self.gamestate == Serve.PASS:
                self.gamestate = Serve.FINISHED
            else:
                self.gamestate = Serve.PASS
        else:
            self.showboard()

    def serve(self):
        #avoid the "new room quick message" bug
        sleep(.5)

        p("serving game!")

        self.gnugo = Gnugo()

        sz = self.get_int("What boardsize would you like? (19):", 3, 19, 19)
        self.gnugo.command("boardsize", sz)

        handicap = self.get_int("What handicap would you like? (0):", 0, 12, 0)
        if handicap > 0:
            self.gnugo.command("fixed_handicap", handicap)

        self.showboard()

        if handicap == 0:
            self.get_human_move("black")
        else:
            self.white = Serve.HUMAN
            self.black = Serve.COMPUTER

        #now black will have played, either via handicap or the previous command,
        #so white will go next.
        while self.gamestate != Serve.FINISHED:
            if self.white == Serve.HUMAN:
                self.get_human_move("white")
            else:
                self.get_computer_move("white")

            if self.gamestate == Serve.FINISHED: break

            if self.black == Serve.HUMAN:
                self.get_human_move("black")
            else:
                self.get_computer_move("black")

        score = self.gnugo.command("final_score").split()[1]
        self.send("Final Score: %s" % score)
