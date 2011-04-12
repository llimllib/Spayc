"""Wrap a connection to a gnugo process"""
from subprocess import Popen, PIPE

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
