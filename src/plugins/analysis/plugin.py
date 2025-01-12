"""Analysis RAPD plugin"""

"""
This file is part of RAPD

Copyright (C) 2011-2018, Cornell University
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

__created__ = "2011-02-02"
__maintainer__ = "Jon Schuermann"
__email__ = "schuerjp@anl.gov"
__status__ = "Development"

# This is an active RAPD plugin
RAPD_PLUGIN = True
# This plugin's type
DATA_TYPE = "MX"
PLUGIN_TYPE = "ANALYSIS"
PLUGIN_SUBTYPE = "CORE"
# A unique UUID for this handler (uuid.uuid1().hex[:4])
ID = "f068"
# Version of this plugin
VERSION = "2.0.0"

# Standard imports
import base64
from distutils.spawn import find_executable
import logging
from multiprocessing import Process, Queue
from threading import Thread
from Queue import Queue as tqueue
import os
from pprint import pprint
import shutil
import subprocess
import sys
import time
import unittest
import numpy
import shlex
import importlib

# RAPD imports
import plugins.subcontractors.molrep as molrep
import plugins.subcontractors.parse as parse
# import plugins.subcontractors.precession as precession
import plugins.subcontractors.xtriage as xtriage
#from plugins.subcontractors.rapd_cctbx import get_pdb_info
from plugins.subcontractors.rapd_phaser import run_phaser_module

import utils.credits as rcredits
import utils.exceptions as exceptions
from utils.text import json
from bson.objectid import ObjectId
import utils.xutils as xutils
from utils.processes import local_subprocess
import info
import plugins.pdbquery.commandline
import plugins.pdbquery.plugin

# Software dependencies
VERSIONS = {
    "gnuplot": (
        "gnuplot 4.2",
        "gnuplot 5.0",
    ),
    "phenix": (
        "Version: 1.11.1",
    )
}
# Setup multiprocessing.Pool to launch jobs
#POOL = process.mp_pool(4)

class RapdPlugin(Process):
    """
    RAPD plugin class

    Command format:
    {
       "command":"analysis",
       "directories":
           {
               "work": ""                          # Where to perform the work
           },
       "site_parameters": {}                       # Site data
       "preferences": {}                           # Settings for calculations
       "return_address":("127.0.0.1", 50000)       # Location of control process
    }
    """

    input_sg = None
    cell = None
    cell_output = Queue()
    sample_type = "protein"
    solvent_content = 0.55
    # test = True
    volume = None
    # Set initital status so we can add to it
    status = 1

    # Set the timer from info.py
    if getattr(info, "STATS_TIMER", False):
        stats_timer = info.STATS_TIMER
    else:
        stats_timer = 180

    do_molrep = True
    do_phaser = True

    #xtriage_output_raw = None
    #molrep_output_raw = None
    #phaser_results = None
    
    redis = False

    jobs = {}


    results = {
        "command": None,
        "parsed": {},
        "raw": {},
        "process": {}
    }

    def __init__(self, command, processed_results=False, tprint=False, logger=False, verbosity=False):
        """Initialize the plugin"""

        # Keep track of start time
        self.start_time = time.time()

        # If the logging instance is passed in...
        if logger:
            self.logger = logger
        else:
            # Otherwise get the logger Instance
            self.logger = logging.getLogger("RAPDLogger")
            self.logger.debug("__init__")
        
        self.verbose = verbosity

        # Used for sending results back to DB
        self.processed_results = processed_results

        # Store tprint for use throughout
        if tprint:
            self.tprint = tprint
        # Dead end if no tprint passed
        else:
            def func(arg=False, level=False, verbosity=False, color=False):
                pass
            self.tprint = func

        # Some logging
        if self.verbose and self.logger:
            self.logger.info(command)
        # pprint(command)

        # Store passed-in variables
        self.command = command
        self.preferences = command.get("preferences", {})

        self.results["process"] = {
            "process_id": self.command.get("process_id"),
            "status": 1}

        self.db_settings = self.command["input_data"].get("db_settings")

        # Start up processing
        Process.__init__(self, name="analysis")

    def run(self):
        """Execution path of the plugin"""
        #self.finish_phaser_ncs()
        self.preprocess()
        self.process()
        self.postprocess()

    def preprocess(self):
        """Set up for plugin action"""

        # self.tprint("preprocess")
        if self.verbose and self.logger:
            self.logger.debug("preprocess")
        self.tprint(arg=0, level="progress")

        # Handle sample type from commandline
        if not self.preferences["sample_type"] == "default":
            self.sample_type = self.preferences["sample_type"]

        # Make the work_dir if it does not exist.
        if os.path.exists(self.command["directories"]["work"]) == False:
            os.makedirs(self.command["directories"]["work"])

        # Change directory to the one specified in the incoming dict
        os.chdir(self.command["directories"]["work"])

        self.data_file = self.command["input_data"]["data_file"]

        # Get information from the data file
        self.input_sg, self.cell, self.volume = \
            xutils.get_mtz_info(datafile=self.data_file)

        self.tprint("\nReading in datafile", level=30, color="blue")
        self.tprint("  Spacegroup: %s" % self.input_sg, level=20, color="white")
        self.tprint("  Cell: %s" % str(self.cell), level=20, color="white")
        self.tprint("  Volume: %f" % self.volume, level=20, color="white")

        # Handle ribosome sample types
        # FIX THIS SINCE IT WILL ALWAYS BE default!!
        if (self.preferences["sample_type"] != "default" and \
            self.volume > 25000000.0) or \
            self.preferences["sample_type"] == "ribosome": #For 30S
            self.sample_type = "ribosome"
            self.solvent_content = 0.64
            self.stats_timer = 300

        self.tprint("  Sample type: %s" % self.sample_type, level=20, color="white")
        self.tprint("  Solvent content: %s" % self.solvent_content, level=20, color="white")

        # Get some data back into the command
        self.preferences["sample_type"] = self.sample_type
        self.preferences["solvent_content"] = self.solvent_content

        # Construct the results object
        self.construct_results()

        # if self.test:
        #     self.logger.debug("TEST IS SET \"ON\"")

        # Check for dependency problems
        self.check_dependencies()

    def check_dependencies(self):
        """Make sure dependencies are all available"""

        # If no gnuplot turn off printing
        if self.preferences.get("show_plots", True) and (not self.preferences.get("json", False)):
            if not find_executable("gnuplot"):
                self.tprint("\nExecutable for gnuplot is not present, turning off plotting",
                            level=30,
                            color="red")
                self.preferences["show_plots"] = False

        # If no phenix.xtriage, dead in the water
        if not find_executable("phenix.xtriage"):
            self.tprint("Executable for phenix.xtriage is not present, exiting",
                        level=30,
                        color="red")
            self.results["process"]["status"] = -1
            self.results["error"] = "Executable for phenix.xtriage is not present"
            self.write_json(self.results)
            raise exceptions.MissingExecutableException("phenix.xtriage")

        # If no molrep, skip it
        if not find_executable("molrep"):
            self.tprint("\nExecutable for molrep is not present, turning off self rotation \
calculation",
                        level=30,
                        color="red")
            self.do_molrep = False

        # If no phaser, skip it
        if not find_executable("phenix.phaser"):
            self.tprint("\nExecutable for phaser is not present, turning off analysis",
                        level=30,
                        color="red")
            self.do_phaser = False

    def construct_results(self):
        """Create the self.results dict"""

        # Copy over details of this run
        self.results["command"] = self.command.get("command")
        self.results["preferences"] = self.preferences
        self.results["results"] = {"raw":{}, "parsed":{}}

        # Describe the process
        self.results["process"] = self.command.get("process", {})
        # Status is now 1 (starting)
        self.results["process"]["status"] = self.status
        # Process type is plugin
        self.results["process"]["type"] = "plugin"
        # Give it a result_id
        self.results["process"]["result_id"] = str(ObjectId())
        
        # Add link to processed dataset
        if self.processed_results:
            #self.results["process"]["result_id"] = self.processed_results["process"]["result_id"]
            # This links to MongoDB results._id
            self.results["process"]["parent_id"] = self.processed_results.get("process", {}).get("result_id", False)
            # This links to a session
            self.results["process"]["session_id"] = self.processed_results.get("process", {}).get("session_id", False)
            # Identify parent type
            self.results["process"]["parent"] = self.processed_results.get("plugin", {})
            # The repr
            self.results["process"]["repr"] = self.processed_results.get("process", {}).get("repr", "Unknown")

        # Describe plugin
        self.results["plugin"] = {
            "data_type":DATA_TYPE,
            "type":PLUGIN_TYPE,
            "subtype":PLUGIN_SUBTYPE,
            "id":ID,
            "version":VERSION
        }
    
    def connect_to_redis(self):
        """Connect to the redis instance"""
        # Create a pool connection
        redis_database = importlib.import_module('database.redis_adapter')
        #redis_database = redis_database.Database(settings=self.db_settings)
        #self.redis = redis_database.connect_to_redis()
        self.redis = redis_database.Database(settings=self.db_settings,
                                             logger=self.logger)

    def send_results(self):
        """Let everyone know we are working on this"""

        self.logger.debug("send_results")

        if self.preferences.get("run_mode") == "server":

            self.logger.debug("Sending back on redis")

            #self.logger.debug(self.results)

            #if results.get('results', False):
            #    if results['results'].get('data_produced', False):
            #        pprint(results['results'].get('data_produced'))

            # Transcribe results
            json_results = json.dumps(self.results)

            # Get redis instance
            if not self.redis:
                self.connect_to_redis()

            # Send results back
            self.redis.lpush("RAPD_RESULTS", json_results)
            self.redis.publish("RAPD_RESULTS", json_results)

    
    def update_status(self):
        """Update the status and send back results."""
        if self.status == 1:
            self.status = 25
        else:
            self.status += 25
        if self.status > 90:
            self.status = 90
        self.results["process"]["status"] = self.status

    def process(self):
        """Run plugin action"""
        if self.verbose and self.logger:
            self.logger.debug("preprocess")

        self.tprint("\nAnalyzing the data file", level=30, color="blue")
        
        self.run_xtriage()
        self.tprint(arg=10, level="progress")
        self.run_molrep()
        self.tprint(arg=20, level="progress")
        self.run_phaser_ncs()
        self.tprint(arg=30, level="progress")
        # self.run_labelit_precession()
        # self.tprint(arg=40, level="progress")

        self.jobs_monitor()

    def postprocess(self):
        """Clean up after plugin action"""
        if self.verbose and self.logger:
            self.logger.debug("postprocess")
        # self.tprint("postprocess", level=10, color="white")

        # Output to terminal
        self.print_xtriage_results()
        self.print_plots()

        # Cleanup my mess.
        self.clean_up()

        # Finished
        self.results["process"]["status"] = 100
        self.tprint(arg=100, level="progress")

        # Handle JSON output
        self.write_json()

        # Notify inerested party
        #self.handle_return()
        self.send_results()

        # Write credits to screen
        self.print_credits()
        
        # Message in logger
        self.logger.debug('Analysis finished')

    def jobs_monitor(self):
        """Monitor running jobs and finsh them when they complete."""
        timed_out = False
        timer = 0
        jobs = self.jobs.keys()
        if jobs != ['None']:
            counter = len(jobs)
            while counter != 0:
                for job in jobs:
                    if job.is_alive() == False:
                        if self.jobs[job].get('name') == 'xtriage':
                            self.finish_xtriage()
                        if self.jobs[job].get('name') == 'molrep':
                            self.finish_molrep()
                        if self.jobs[job].get('name') == 'NCS':
                            self.finish_phaser_ncs()
                        jobs.remove(job)
                        del self.jobs[job]
                        counter -= 1
                time.sleep(0.2)
                timer += 0.2
                """
                if self.verbose:
                  if round(timer%1,1) in (0.0,1.0):
                      print 'Waiting for AutoStat jobs to finish '+str(timer)+' seconds'
                """
                if self.stats_timer:
                    if timer >= self.stats_timer:
                        timed_out = True
                        break
            if timed_out:
                if self.verbose:
                    self.logger.debug('AutoStat timed out.')
                    print 'AutoStat timed out.'
                
                pids = [self.jobs[job].get('pid') for job in self.jobs]
                for pid in pids:
                    xutils.kill_children(pid, self.logger)
                """
                for pid in self.pids.values():
                    #jobs are not sent to cluster
                    Utils.killChildren(self,pid)
                for job in jobs:
                    if self.jobs_output[job] == 'xtriage':
                        self.postprocessXtriage()
                    if self.jobs_output[job] == 'molrep':
                        self.postprocessMolrep()
                    if self.jobs_output[job] == 'NCS':
                        self.postprocessNCS()
                """
            if self.verbose:
                self.logger.debug('AutoStats Queue finished.')


    def run_xtriage(self):
        """
        Run Xtriage and the parse the output

        Xtriage has to be run and the log file read in as the log file has more information than
        reported to STDOUT
        """
        if self.verbose and self.logger:
            self.logger.debug("run_xtriage")
        self.tprint("  Running xtriage", level=30, color="white")

        command = "phenix.xtriage %s scaling.input.xray_data.obs_labels=\"I(+),\
                  SIGI(+),I(-),SIGI(-)\" scaling.input.parameters.reporting.loggraphs=True" % \
                  self.data_file

        if self.verbose and self.logger:
            self.logger.debug(command)

        pid_queue = Queue()
        job = Process(target=local_subprocess, kwargs={'command': command,
                                                        'pid_queue':pid_queue})
        job.start()
        self.jobs[job] = {'name': 'xtriage',
                          'pid': pid_queue.get()}

    def finish_xtriage(self):
        if self.verbose and self.logger:
            self.logger.debug('finish_xtriage')
        # Read raw output
        if os.path.exists("logfile.log"):
            self.results["results"]["raw"]["xtriage"] = open("logfile.log", "r").readlines()

            # Move logfile.log
            shutil.move("logfile.log", "xtriage.log")

            self.results["results"]["parsed"]["xtriage"] = \
                xtriage.parse_raw_output(raw_output=self.results["results"]["raw"]["xtriage"],
                                        logger=self.logger)
        # No log file
        else:
            self.results["results"]["raw"]["xtriage"] = False
            self.results["results"]["parsed"]["xtriage"] = False

        # Update the status number
        self.update_status()
        # return results
        self.send_results()

    def run_molrep(self):
        """Run Molrep to calculate self rotation function"""
        if self.verbose and self.logger:
            self.logger.debug("run_molrep")

        if self.do_molrep:

            self.tprint("  Calculating self rotation function",
                        level=30,
                        color="white")

            command = "molrep -f %s -i <<stop\n_DOC  Y\n_RESMAX 4\n_RESMIN 9\nstop" % \
                      self.data_file

            molrep_queue = Queue()
            job = Process(target=local_subprocess, kwargs={'command': command,
                                                           #'result_queue': self.molrep_queue,
                                                           #'logfile' : "molrep_selfrf.log",
                                                           'pid_queue':molrep_queue,
                                                           'shell': True})
            job.start()
            self.jobs[job] = {'name': 'molrep',
                              'pid': molrep_queue.get()}

    def finish_molrep(self):
        """Get Molrep results"""
        if self.verbose and self.logger:
            self.logger.debug('finish_molrep')

        jobs = {}
        # Store raw output
        log = open('molrep.doc','r').readlines()
        self.results["results"]["raw"]["molrep"] = log

        # Parse the Molrep log
        parsed_molrep_results = molrep.parse_raw_output(log)

        # Convert the Molrep postscript file to JPEG, if convert is available
        crop_sizes = {
            "60": "254X305+265+410",
            "90": "254X305+265+110",
            "120": "256X305+10+410",
            "180": "256X305+10+110",
        }
        # Launch all the jobs
        results_queue = {}
        convert_executables = ("convert", "/usr/local/bin/convert")
        for convert_executable in convert_executables:
            # print "Trying %s" % convert_executable
            if find_executable(convert_executable):
                for label, size in crop_sizes.iteritems():
                    command = [convert_executable,
                               "molrep_rf.ps",
                               "-crop",
                               size,
                               "-quality",
                               "50",
                               "molrep_rf_%s.jpg" % label]

                    results_queue[label] = tqueue()
                    job = Thread(target=local_subprocess, kwargs={'command': command,
                                                                 'result_queue': results_queue[label],
                                                                 'pid_queue':results_queue[label]})
                    job.start()
                    jobs[job] = {'name': label,
                                 'pid': results_queue[label].get()}
                # Wait for jobs to complete and gather results
                while len(jobs.keys()):
                    for job in jobs.keys():
                        if not job.is_alive():
                            label = jobs[job].get('name')
                            del jobs[job]
                            output = results_queue[label].get()
                            if output.get('stderr'):
                                self.tprint("  Unable to convert postscript to jpeg. Imagemagick needs to be installed",
                                            level=30,
                                            color="red")
                                parsed_molrep_results["self_rotation_images"] = False
                                break
                            else:
                                parsed_molrep_results["self_rotation_images"] = True
                                parsed_molrep_results["self_rotation_imagefile_%s" % label] = os.path.abspath("molrep_rf_%s.jpg" % label)
                                # read in the image and encode
                                with open("molrep_rf_%s.jpg" % label, "rb") as image_file:
                                    encoded_string = base64.b64encode(image_file.read())
                                    parsed_molrep_results["self_rotation_image_%s" % label] = "data:image/jpeg;base64,"+encoded_string
                # Break out of the loop trying multiple convert executables
                if parsed_molrep_results["self_rotation_images"]:
                    break
            else:
                self.tprint("  Unable to convert postscript to jpeg. Imagemagick needs to be installed",
                            level=30,
                            color="red")
                parsed_molrep_results["self_rotation_image"] = False

        self.results["results"]["parsed"]["molrep"] = parsed_molrep_results
        # Update the status number and return results
        self.update_status()
        # return results
        self.send_results()

    def run_phaser_ncs_NEW(self): # USe module in plugins.subcontractors.python_phaser
        """Run Phaser tNCS and anisotropy correction
           This Python version is having problems generating a readable loggraph
        """
        if self.verbose and self.logger:
            self.logger.debug("run_phaser_ncs")

        if self.do_phaser:

            self.tprint("  Analyzing NCS and anisotropy",
                        level=30,
                        color="white")

            self.phaser_queue = Queue()
            job = Process(target=run_phaser_module, kwargs={'data_file': self.data_file,
                                                            'result_queue': self.phaser_queue,
                                                            'tncs': True})
            job.start()
            self.jobs[job] = {'name': 'NCS',
                              'pid': job.pid}

    def run_phaser_ncs(self): # USe module in plugins.subcontractors.python_phaser
        """Run Phaser tNCS and anisotropy correction"""
        if self.verbose and self.logger:
            self.logger.debug("run_phaser_ncs")

        if self.do_phaser:

            self.tprint("  Analyzing NCS and anisotropy",
                        level=30,
                        color="white")

            command = "phenix.phaser << eof\nMODE NCS\nHKLIn %s\nLABIn F=F SIGF=SIGF\neof\n" % \
                      self.data_file
            
            self.phaser_queue = Queue()
            job = Process(target=local_subprocess, kwargs={'command': command,
                                                           'result_queue': self.phaser_queue,
                                                           'logfile' : "phaser_ncs.log",
                                                           'pid_queue':self.phaser_queue,
                                                           'shell': True})
            job.start()
            self.jobs[job] = {'name': 'NCS',
                              'pid': self.phaser_queue.get()}

    def finish_phaser_ncs(self):
        if self.verbose and self.logger:
            self.logger.debug('finish_phaser_ncs')

        # Store raw output
        output = self.phaser_queue.get()
        self.results["results"]["raw"]["phaser"] = output['stdout'].split("\n")

        self.results["results"]["parsed"]["phaser"] = parse.parse_phaser_ncs_output(output['stdout'])

        # Update the status number and return results
        self.update_status()
        # return results
        self.send_results()

    # def run_labelit_precession(self):
    #     """Run labelit to make precession photos"""
    #
    #     precession.LabelitPP(input=[
    #         {
    #             "run":
    #         }], output=None, logger=self.logger)

    def clean_up(self):
        """Clean up the working directory"""

        self.logger.debug("clean_up")
        # self.tprint("  Cleaning up", level=30, color="white")

        if self.preferences.get("clean", False):

            self.logger.debug("Cleaning up Analysis files and folders")
            #TODO
            # Change to work dir
            os.chdir(self.command["directories"]["work"])

            # # Gather targets and remove
            #TODO
            # files_to_clean = glob.glob("Phaser_*")
            # for target in files_to_clean:
            #     shutil.rmtree(target)

    def handle_return_OLD(self):
        """Output data to consumer"""

        self.logger.debug("handle_return")

        run_mode = self.preferences["run_mode"]

        if run_mode == "interactive":
            pass
        elif run_mode == "json":
            pass
        elif run_mode == "server":
            # print "handle_return >> server"
            if self.command["queue"]:
                self.command["queue"].put(self.results)
        elif run_mode == "subprocess":
            # print "handle_return >> subprocess"
            if self.command["queue"]:
                self.command["queue"].put(self.results)
        elif run_mode == "subprocess-interactive":
            # print "handle_return >> subprocess-interactive"
            if self.command["queue"]:
                self.command["queue"].put(self.results)

    def print_results(self):
        """Print the results to the commandline"""

        self.print_xtriage_results()
        self.print_plots()

    def write_json(self):
        """Output JSON-formatted results to terminal"""

        json_results = json.dumps(self.results)

        # Write the results to a JSON-encoded file
        with open("result.json", "w") as out_file:
            out_file.write(json_results)

        # If running in JSON mode, print to terminal
        if self.preferences.get("run_mode") == "json":
            print json_results

    def print_xtriage_results(self):
        """Print out the xtriage results"""

        xtriage_results = self.results["results"]["parsed"]["xtriage"]

        if xtriage_results:

            self.tprint("\nXtriage results", level=99, color="blue")

            self.tprint("  Input spacegroup: %s (%d)" % (
                xtriage_results["spacegroup"]["text"],
                xtriage_results["spacegroup"]["number"]),
                        level=99,
                        color="white")

            self.tprint("\n  Input unit cell: a= %.2f      b= %.2f     c= %.2f" % (
                xtriage_results["unit_cell"]["a"],
                xtriage_results["unit_cell"]["b"],
                xtriage_results["unit_cell"]["c"]),
                        level=99,
                        color="white")
            self.tprint("                   alpha= %.2f  beta= %.2f  gamma= %.2f" % (
                xtriage_results["unit_cell"]["alpha"],
                xtriage_results["unit_cell"]["beta"],
                xtriage_results["unit_cell"]["gamma"]),
                        level=99,
                        color="white")

            self.tprint("\n  Patterson analysis (off-origin peaks)", level=99, color="white")
            self.tprint("                height % of   dist from    fractional coords",
                        level=99,
                        color="white")
            self.tprint("  #   p-value   origin peak     origin      x      y      z",
                        level=99,
                        color="white")
            for peak_id, peak_data in xtriage_results["Patterson peaks"].iteritems():
                self.tprint("  {}   {:6.4f}     {:5.2f}%         {:5.2f}    {:5.3f}  {:5.3f}  {:5.3f}"\
                    .format(peak_id,
                            peak_data["p-val"],
                            peak_data["peak"]*100.0,
                            peak_data["dist"],
                            peak_data["frac x"],
                            peak_data["frac y"],
                            peak_data["frac z"]),
                            level=99,
                            color="white")

            self.tprint("\n  Xtriage verdict\n", level=99, color="white")
            for line in xtriage_results["verdict_text"]:
                self.tprint("    %s" % line, level=99, color="white")

        else:
            self.tprint("\nNo Xtriage results", level=99, color="red")

    def print_plots(self):
        """Print plots to the terminal"""

        if "interactive" in self.preferences.get("run_mode"):

            if self.preferences.get("show_plots", False):

                if self.results["results"]["parsed"]["xtriage"]:

                    xtriage_plots = self.results["results"]["parsed"]["xtriage"]["plots"]
                    # pprint(xtriage_plots.keys())

                    self.tprint("\nPlots", level=99, color="blue")

                    # Determine the open terminal size
                    term_size = os.popen('stty size', 'r').read().split()

                    # The intensity plot
                    for plot_label in ("Intensity plots",
                                       "Measurability of Anomalous signal",
                                       "NZ test",
                                       "L test, acentric data",):

                        # Skip the plot if it's not available
                        if not plot_label in xtriage_plots:
                            continue

                        # print plot_label
                        # pprint(xtriage_plots[plot_label])

                        # The plot data
                        plot_parameters = xtriage_plots[plot_label]["parameters"]
                        plot_data = xtriage_plots[plot_label]["data"]

                        # pprint(plot_parameters)
                        # pprint(plot_data)

                        # Settings for each plot
                        if plot_label == "Intensity plots":
                            plot_title = "Intensity vs. Resolution"
                            x_axis_label = "Resolution (A)"
                            y_axis_label = "Intensity"
                            line_label = y_axis_label
                            reverse = True
                            plot_data = (plot_data[0],)
                        elif plot_label == "Measurability of Anomalous signal":
                            plot_title = "Anomalous Measurability"
                            x_axis_label = "Resolution (A)"
                            y_axis_label = "Measurability"
                            line_label = "Measured"
                            # Line for what is meaningful signal
                            y2s = [0.05,] * len(plot_data[0]["series"][0]["ys"])
                            line_label_2 = "Meaningful"
                            reverse = True
                            plot_data = (plot_data[0],)
                        elif plot_label in ("NZ test", "L test, acentric data"):
                            # pprint(plot_parameters)
                            # pprint(plot_data)
                            plot_title = plot_parameters["toplabel"]
                            x_axis_label = plot_parameters["x_label"]
                            y_axis_label = ""

                        # Determine plot extent
                        y_array = numpy.array(plot_data[0]["series"][0]["ys"])
                        y_max = y_array.max() * 1.1
                        y_min = 0
                        x_array = numpy.array(plot_data[0]["series"][0]["xs"])
                        x_max = x_array.max()
                        x_min = x_array.min()

                        # Special y_max & second y set
                        if plot_label == "Measurability of Anomalous signal":
                            y_max = max(0.055, y_max)

                        gnuplot = subprocess.Popen(["gnuplot"],
                                                   stdin=subprocess.PIPE,
                                                   stderr=subprocess.PIPE)

                        gnuplot.stdin.write("""set term dumb %d,%d
                                               set title '%s'
                                               set xlabel '%s'
                                               set ylabel '%s' rotate by 90 \n""" %
                                            (int(term_size[1])-20,
                                             30,
                                             plot_title,
                                             x_axis_label,
                                             y_axis_label))

                        # Create the plot string
                        if reverse:
                            plot_string = "plot [%f:%f] [%f:%f] " \
                                              % (x_max, x_min, y_min, y_max)
                        else:
                            plot_string = "plot [%f:%f] [%f:%f] " \
                                              % (x_min, x_max, y_min, y_max)
                        # Mark the minimum measurability
                        if plot_label == "Measurability of Anomalous signal":
                            plot_string += "'-' using 1:2 with lines title '%s', " % line_label_2
                            plot_string += "'-' using 1:2 with lines title '%s'\n" % line_label

                        elif plot_label in ("NZ test", "L test, acentric data"):
                            for index, data in enumerate(plot_data):
                                line_label = data["parameters"]["linelabel"]
                                plot_string += "'-' using 1:2 with lines title '%s' " % line_label
                                if index == len(plot_data) - 1:
                                    plot_string += "\n"
                                else:
                                    plot_string += ", "

                        else:
                            plot_string += "'-' using 1:2 title '%s' with lines\n" % line_label

                        gnuplot.stdin.write(plot_string)


                        # Mark the minimum measurability
                        if plot_label == "Measurability of Anomalous signal":
                            # Run through the data and add to gnuplot
                            for plot in plot_data:
                                xs = plot["series"][0]["xs"]
                                ys = plot["series"][0]["ys"]
                                # Minimal impact line
                                for x_val, y_val in zip(xs, y2s):
                                    gnuplot.stdin.write("%f %f\n" % (x_val, y_val))
                                gnuplot.stdin.write("e\n")
                                # Experimental line
                                for x_val, y_val in zip(xs, ys):
                                    # print x_val, y_val, y2_val
                                    gnuplot.stdin.write("%f %f\n" % (x_val, y_val))
                                gnuplot.stdin.write("e\n")
                        else:
                            # Run through the data and add to gnuplot
                            for plot in plot_data:
                                xs = plot["series"][0]["xs"]
                                ys = plot["series"][0]["ys"]
                                for x_val, y_val in zip(xs, ys):
                                    gnuplot.stdin.write("%f %f\n" % (x_val, y_val))
                                gnuplot.stdin.write("e\n")

                        # Now plot!
                        gnuplot.stdin.flush()
                        time.sleep(2)
                        gnuplot.terminate()
                else:
                    self.tprint("\nSorry, no plots", level=99, color="red")

    def print_credits(self):
        """Print information on programs used to the terminal"""

        self.tprint(rcredits.HEADER.replace("RAPD", "RAPD analysis"),
                    level=99,
                    color="blue")

        programs = ["CCTBX", "MOLREP", "PHENIX", "PHASER"]
        info_string = rcredits.get_credits_text(programs, "    ")

        self.tprint(info_string, level=99, color="white")

def get_commandline():
    """Grabs the commandline"""

    print "get_commandline"

    # Parse the commandline arguments
    commandline_description = "Test analysis plugin"
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

        commandline_args = get_commandline()

        main(args=commandline_args)
