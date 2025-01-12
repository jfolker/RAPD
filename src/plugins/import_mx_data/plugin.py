"""import_mx_data RAPD plugin"""

"""
This file is part of RAPD

Copyright (C) 2019, Cornell University
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

__created__ = "2019-07-31"
__maintainer__ = "Frank Murphy"
__email__ = "fmurphy@anl.gov"
__status__ = "Development"

# This is an active RAPD plugin
RAPD_PLUGIN = True

# This plugin's types
DATA_TYPE = "MX"  # MX, ?PLUGIN_TYPE = "IMPORT_MX_DATA"
PLUGIN_SUBTYPE = "EXPERIMENTAL"

# A unique ID for this handler (uuid.uuid1().hex[:4])
ID = "b257"
VERSION = "1.0.0"

# Standard imports
# import argparse
# import from collections import OrderedDict
# import datetime
import glob
import json
import logging
# import math
import multiprocessing
import os
# import pprint
# import pymongo
# import re
# import redis
import shutil
import subprocess
import sys
import time
# import unittest
# import urllib2
import uuid
from distutils.spawn import find_executable

# RAPD imports
# import commandline_utils
# import detectors.detector_utils as detector_utils
# import utils
# import utils.credits as rcredits
import info
from utils import exceptions

# Software dependencies
VERSIONS = {
    "gnuplot": (
        "gnuplot 4.2",
        "gnuplot 5.0",
    )
}

class RapdPlugin(multiprocessing.Process):
    """
    RAPD plugin class

    Command format:
    {
       "command":"import_mx_data",
       "directories":
           {
               "work": ""                          # Where to perform the work
           },
       "site_parameters": {}                       # Site data
       "preferences": {}                           # Settings for calculations
       "return_address":("127.0.0.1", 50000)       # Location of control process
    }
    """

    # Holders for passed-in info
    command = None
    preferences = None

    # Holders for results
    results = {}

    def __init__(self, command, tprint=False, logger=False):
        """Initialize the plugin"""

        # If the logging instance is passed in...
        if logger:
            self.logger = logger
        else:
            # Otherwise get the logger Instance
            self.logger = logging.getLogger("RAPDLogger")
            self.logger.debug("__init__")

        # Keep track of start time
        self.start_time = time.time()

        # Store tprint for use throughout
        if tprint:
            self.tprint = tprint
        # Dead end if no tprint passed
        else:
            def func(*args, *kwargs):
                pass
            self.tprint = func

        # Some logging
        self.logger.info(command)

        # Store passed-in variables
        self.command = command
        self.preferences = self.command.get("preferences", {})

        # Set up the results with command and process data
        self.results["command"] = command

        # Create a process section of results with the id and a starting status of 1
        self.results["process"] = {
            "process_id": self.command.get("process_id"),
            "status": 1}

        multiprocessing.Process.__init__(self, name="import_mx_data")
        self.start()

    def run(self):
        """Execution path of the plugin"""

        self.preprocess()
        self.process()
        self.postprocess()
        self.print_credits()

    def preprocess(self):
        """Set up for plugin action"""

        self.tprint(arg=0, level="progress")
        self.tprint("preprocess")

        # Check for dependency problems
        self.check_dependencies()

    def process(self):
        """Run plugin action"""

        self.tprint("process")

    def postprocess(self):
        """Events after plugin action"""

        self.tprint("postprocess")

        self.tprint(arg=99, level="progress")
        # Clean up mess
        self.clean_up()

        # Send back results
        self.handle_return()

    def check_dependencies(self):
        """Make sure dependencies are all available"""

        # A couple examples from index plugin
        # Can avoid using best in the plugin b        # If no best, switch to mosflm for strategy
        # if self.strategy == "best":
        #     if not find_executable("best"):
        #         self.tprint("Executable for best is not present, using Mosflm for strategy",
        #                     level=30,
        #                     color="red")
        #         self.strategy = "mosflm"

        # If no gnuplot turn off printing
        # if self.preferences.get("show_plots", True) and (not self.preferences.get("json", False)):
        #     if not find_executable("gnuplot"):
        #         self.tprint("\nExecutable for gnuplot is not present, turning off plotting",
        #                     level=30,
        #                     color="red")
        #         self.preferences["show_plots"] = False

        # If no labelit.index, dead in the water
        # if not find_executable("labelit.index"):
        #     self.tprint("Executable for labelit.index is not present, exiting",
        #                 level=30,
        #                 color="red")
        #     self.results["process"]["status"] = -1
        #     self.results["error"] = "Executable for labelit.index is not present"
        #     self.write_json(self.results)
        #     raise exceptions.MissingExecutableException("labelit.index")

        # If no raddose, should be OK
        # if not find_executable("raddose"):
        #     self.tprint("\nExecutable for raddose is not present - will continue",
        #                 level=30,
        #                 color="red")

    def clean_up(self):
        """Clean up after plugin action"""

        self.tprint("clean_up")

    def handle_return(self):
        """Output data to consumer - still under construction"""

        self.tprint("handle_return")

        run_mode = self.command["preferences"]["run_mode"]

        # Handle JSON At least write to file
        self.write_json()

        # Print results to the terminal
        if run_mode == "interactive":
            self.print_results()
        # Traditional mode as at the beamline
        elif run_mode == "server":
            pass
        # Run and return results to launcher
        elif run_mode == "subprocess":
            return self.results
        # A subprocess with terminal printing
        elif run_mode == "subprocess-interactive":
            self.print_results()
            return self.results

        def write_json(self):
            """Print out JSON-formatted result"""

            json_string = json.dumps(self.results)

            # Output to terminal?
            if self.preferences.get("json", False):
                print json_string

            # Always write a file
            os.chdir(self.working_dir)
            with open("result.json", "w") as outfile:
                outfile.writelines(json_string)
    def print_credits(self):
        """Print credits for programs utilized by this plugin"""

        self.tprint("print_credits")

        self.tprint(rcredits.HEADER, level=99, color="blue")

        programs = ["CCTBX"]
        info_string = rcredits.get_credits_text(programs, "    ")
        self.tprint(info_string, level=99, color="white")

def get_commandline():
    """Grabs the commandline"""

    print "get_commandline"

    # Parse the commandline arguments
    commandline_description = "Test import_mx_data plugin"
    my_parser = argparse.ArgumentParser(description=commandline_description)

    # A True/False flag
    my_parser.add_argument("-q", "--quiet",
                           action="store_false",
                           dest="verbose",
                           help="Reduce output")

    args = my_parser.parse_args()

    # Insert logic to check or modify args here

    return args

def main(args):
    """
    The main process docstring
    This function is called when this module is invoked from
    the commandline
    """

    if args.verbose:
        verbosity = 2
    else:
        verbosity = 1

    unittest.main(verbosity=verbosity)

    if __name__ == "__main__":

        main()

