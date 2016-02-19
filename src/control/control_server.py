"""
This file is part of RAPD

Copyright (C) 2009-2016, Cornell University
All rights reserved.

RAPD is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, version 3.

RAPD is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__created__ = "2009-07-10"
__maintainer__ = "Frank Murphy"
__email__ = "fmurphy@anl.gov"
__status__ = "Production"

import socket
import threading
import json
import time
import logging, logging.handlers


class ControllerServer(threading.Thread):
    """
    Runs the socket server and spawns new threads when connections are received
    """

    Go = True

    def __init__(self, receiver, port):
        """
        The main server thread
        """
        # Get the logger
        self.logger = logging.getLogger("RAPDLogger")
        self.logger.info('ControllerServer::__init__')

        # Initialize the thred
        threading.Thread.__init__(self)

        # Store passed-in variables
        self.receiver = receiver
        self.port = port

        # Start it up
        self.daemon = True
        self.start()

    def run(self):

        HOST = ''

        # Create the socket listener
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST,self.port))

        # This is the "server"
        while(self.Go):
            #print 'listening'
            s.listen(5)
            conn, addr = s.accept()
            tmp = ControllerHandler(conn=conn,
                                    addr=addr,
                                    receiver=self.receiver,
                                    logger=self.logger)

        # If we exit...
        s.close()

    def stop(self):
        self.logger.debug("Received signal to stop")
        self.Go = False


class PerformAction(threading.Thread):
    """
    Manages the dispatch of jobs to the cluster process
    NB that the cluster can be on the localhost or a remote host
    """
    def __init__(self, command, settings):
        """Initialize the class

        Keyword arguments:
        command --
        settings -- Right now only needs to be a dict with the entry CLUSTER_ADDRESS
        """
        self.logger = logging.getLogger("RAPDLogger")
        self.logger.debug("PerformAction::__init__  command:%s", command)

        #initialize the thread
        threading.Thread.__init__(self)

        #store passed-in variable
        self.command = command
        self.settings = settings

        # Start the thread
        self.start()

    def run(self):
        """Start the thread"""

        self.logger.debug("PerformAction::run")

        attempts = 0

        while(attempts < 10):
            attempts += 1
            self.logger.debug("Cluster connection attempt %d", attempts)

            # Connect to the cluster process
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(self.settings["CLUSTER_ADDRESS"])
                break
            except socket.error:
                self.logger.exception("Failed to initialize socket to cluster")
                time.sleep(1)
        else:
            raise RuntimeError("Failed to initialize socket to cluster after %d attempts", attempts)

        # Put the command in rapd server-speak
        message = json.dumps(self.command)
        message = "<rapd_start>" + message + "<rapd_end>"
        MSGLEN = len(message)

        # Send the message
        total_sent = 0
        while total_sent < MSGLEN:
            sent = s.send(message[total_sent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total_sent += sent

        self.logger.debug("Message sent to cluster total_sent:%d", total_sent)

        # Close connection to cluster
        s.close()

        self.logger.debug("Connection to cluster closed")