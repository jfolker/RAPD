"""
This file is part of RAPD

Copyright (C) 2016, Cornell University
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

__created__ = "2016-03-07"
__maintainer__ = "Frank Murphy"
__email__ = "fmurphy@anl.gov"
__status__ = "Development"

"""
Provide generic interface for cluster interactions
"""

# Standard imports
import drmaa
import os
import redis
import subprocess
import time

def checkCluster():
    """
    Quick check run at beginning of pipelines to see if job was subitted to computer cluster node (returns True) or
    run locally (returns False). The pipelines will use this to know whether to subprocess.Process subjobs or submit to
    compute cluster queueing system. This is the master switch for turning on or off a compute cluster.
    """
    import socket
    #Can create a list of names of your compute nodes for checking. Ours all start with 'compute-'.
    if socket.gethostname().startswith('compute-'):
        return True
    else:
        return False

def checkClusterConn(self):
  """
  Check if execution node can talk to head node through port 536. Used for testing to see if
  subjobs can submit jobs on compute cluster. All nodes should have ability to execute jobs.
  """
  if self.verbose:
    self.logger.debug('Utilities::checkClusterConn')
  try:
    command = 'qping -info gadolinium 536 qmaster 1'
    job = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    for line in job.stdout:
      self.logger.debug(line)

  except:
    self.logger.exception('**ERROR in Utils.checkClusterConn**')

def connectCluster(inp, job=True):
  """
  Used by rapd_agent_beamcenter.py or when a user wants to launch jobs from beamline computer,
  which is not a compute node on cluster, this will login to head node and launch job without
  having them have the login info. Can setup with password or ssh host keys.
  """
  import paramiko
  bc = False
  st = ''
  if job:
    command = 'qsub -j y -terse -cwd -b y '
    command += inp
    print command
    print 'Job ID:'
  else:
    command = inp
  #Use this to say job is beam center calculation.
  if inp.startswith('-pe'):
    bc = True
    #Remove previous beam center results from directory before launching new one.
    st = 'rm -rf bc.log phi*.dat\n'
  client = paramiko.SSHClient()
  client.load_system_host_keys()
  client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
  client.connect(hostname='gadolinium',username='necat')
  stdin,stdout,stderr = client.exec_command('cd %s\n%s%s'%(os.getcwd(),st,command))
  #stdin,stdout,stderr = client.exec_command('cd %s\n%s'%(os.getcwd(),command))
  for line in stdout:
    print line.strip()
    if bc:
      return(line.strip())
  client.close()

def processCluster(self, inp, output=False):
    """
    Submit job to cluster using DRMAA (when you are already on the cluster).
    Main script should not end with os._exit() otherwise running jobs could be orphanned.
    To eliminate this issue, setup self.running = multiprocessing.Event(), self.running.set() in main script,
    then set it to False (self.running.clear()) during postprocess to kill running jobs smoothly.
    """

    try:
        s = False
        jt = False
        running = True
        log = False
        queue = False
        smp = 1
        name = False

        # Check if self.running is setup... used for Best and Mosflm strategies
        try:
            temp = self.running
        except AttributeError:
            running = False

        #Parse the input
        if len(inp) == 1:
            command = inp
        elif len(inp) == 2:
            command, log = inp
        #queue is name of cluster queue.
        elif len(inp) == 3:
            command, log, queue = inp
        #smp is parallel environment set to reserve a specific number of cores on a node.
        elif len(inp) == 4:
            command, log, smp, queue = inp
        # name is a redis database name
        else:
            command, log, smp, queue, name = inp

        #set default cluster queue. Some batch queues use general.q.
        if queue == False:
            queue = 'all.q'

        #'-clear' can be added to the options to eliminate the general.q
        options = '-clear -shell y -p -100 -q %s -pe smp %s' % (queue, smp)
        s = drmaa.Session()
        s.initialize()
        jt = s.createJobTemplate()
        jt.workingDirectory=os.getcwd()
        jt.joinFiles=True
        jt.nativeSpecification=options
        jt.remoteCommand=command.split()[0]
        if len(command.split()) > 1:
            jt.args=command.split()[1:]
        if log:
            #the ':' is required!
            jt.outputPath=':%s'%log
        #submit the job to the cluster and get the job_id returned
        job = s.runJob(jt)
        #return job_id.
        if output:
            output.put(job)

        #cleanup the input script from the RAM.
        s.deleteJobTemplate(jt)

        #If multiprocessing.event is set, then run loop to watch until job or script has finished.
        if running:
            #Returns True if job is still running or False if it is dead. Uses CPU to run loop!!!
            decodestatus = {drmaa.JobState.UNDETERMINED: True,
                            drmaa.JobState.QUEUED_ACTIVE: True,
                            drmaa.JobState.SYSTEM_ON_HOLD: True,
                            drmaa.JobState.USER_ON_HOLD: True,
                            drmaa.JobState.USER_SYSTEM_ON_HOLD: True,
                            drmaa.JobState.RUNNING: True,
                            drmaa.JobState.SYSTEM_SUSPENDED: False,
                            drmaa.JobState.USER_SUSPENDED: False,
                            drmaa.JobState.DONE: False,
                            drmaa.JobState.FAILED: False,
                           }
            #Loop to keep hold process while job is running or ends when self.running event ends.
            while decodestatus[s.jobStatus(job)]:
                if self.running.is_set() == False:
                    s.control(job,drmaa.JobControlAction.TERMINATE)
                    self.logger.debug('job:%s terminated since script is done'%job)
                    break
            #time.sleep(0.2)
            time.sleep(1)
        #Otherwise just wait for it to complete.
        else:
            s.wait(job, drmaa.Session.TIMEOUT_WAIT_FOREVER)

        #Exit cleanly, otherwise master node gets event client timeout errors after 600s.
        s.exit()

    except:
        self.logger.exception('**ERROR in Utils.processCluster**')
        #Cleanup if error.
        if s:
            if jt:
                s.deleteJobTemplate(jt)
            s.exit()
    finally:
        if name!= False:
            self.red.lpush(name,1)

def killChildrenCluster(self,inp):
  """
  Kill jobs on cluster. The JobID is sent in and job is killed. Must be launched from
  a compute node on the cluster. Used in pipelines to kill jobs when timed out or if
  a solution in Phaser is found in the first round and the second round jobs are not needed.
  """
  if self.verbose:
    self.logger.debug('Utilities::killChildrenCluster')
  try:
    command = 'qdel %s'%inp
    self.logger.debug(command)
    os.system(command)
  except:
    self.logger.exception('**Could not kill the jobs on the cluster**')

def stillRunningCluster(self,jobid):
  """
  Check to see if process and/or its children and/or children's children are still running. Must
  be launched from compute node.
  """
  try:
    running = False
    if self.cluster_use:
      command = 'qstat'
    else:
      command = 'rapd2.python /gpfs5/users/necat/rapd/gadolinium/trunk/qstat.py'
    output = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    for line in output.stdout:
      if len(line.split()) > 0:
        if line.split()[0] == jobid:
          running = True
    return(running)
  except:
    self.logger.exception('**ERROR in Utils.stillRunningCluster**')

def rocksCommand(self,inp):
  """
  Run Rocks command on all cluster nodes. Mainly used by rapd_agent_beamcenter.py to copy
  specific images to /dev/shm on each node for processing in RAM.
  """
  if self.verbose:
    self.logger.debug('Utilities::rocksCommand')
  try:
    command = '/opt/rocks/bin/rocks run host compute "%s"'%inp
    processLocal("ssh necat@gadolinium '%s'"%command,self.logger)

  except:
      self.logger.exception('**ERROR in Utils.rocksCommand**')