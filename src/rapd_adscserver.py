__author__ = "Frank Murphy"
__copyright__ = "Copyright 2009,2010,2011 Cornell University"
__credits__ = ["Frank Murphy","Jon Schuermann","David Neau","Kay Perry","Surajit Banerjee"]
__license__ = "BSD-3-Clause"
__version__ = "0.9"
__maintainer__ = "Frank Murphy"
__email__ = "fmurphy@anl.gov"
__status__ = "Development"
__date__ = "2009/07/08"

"""
rapd_adscserver provides an xmlrpclib  server that watches xf_status and
marcollect on an adsc data collection computer to provide information back
to rapd_server via to rapd_adsc

If you are adapting rapd to your locality, you will need to check this 
carefully
"""

import socket
import os
import threading 
import time
import atexit
import re
import base64
import logging, logging.handlers
from collections import deque
from SimpleXMLRPCServer import SimpleXMLRPCServer
import MySQLdb,_mysql_exceptions


secrets = { #database information
            'db_host'         : 'my_host',
            'db_user'         : 'my_user',
            'db_password'     : 'passwd-base64encoded',
            'db_data_name'    : 'rapd_data',
            'db_users_name'   : 'rapd_users',
            'db_cloud_name'   : 'rapd_cloud'}

settings = {
               #Beamline
               'beamline.host'  : ('path_to_marcollect','path_to_xf_status','beamline_designation'),
               #DEFAULT
               'default'                  : ('/tmp/marcollect','/tmp/xf_status','T')
           } 


class RAPD_ADSC_Server(threading.Thread):
    """
    Watches the beamline, updates the MySQL database and returns queries
    by the SimpleXMLRPCServer
    """
    def __init__(self,one_run=False):
        
        #set up logging
        LOG_FILENAME = '/tmp/rapd_adscserver.log'
        # Set up a specific logger with our desired output level
        logger = logging.getLogger('RAPDLogger')
        logger.setLevel(logging.DEBUG)
        # Add the log message handler to the logger
        handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=100000, backupCount=5)
        #add a formatter
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        logger.info('RAPD_ADSCSERVER.__init__')

        #init the thread
        threading.Thread.__init__(self)
        
        self.logger     = logger 
        self.ip_address = socket.gethostbyaddr(socket.gethostname())[-1][0]
        
        #passed in
        self.one_run = one_run
        
        #for keeping track of file change times
        self.mar_time = 0
        self.xf_time  = 0
        self.mar_dict = {}
        self.xf_dict  = {}
        self.last_image = False
        self.xf_status_queue = deque()
        self.marcollect_queue = deque()
        
        #initiate connection to MySQL for heartbeat function
        self.Connect2SQL()

        #get our bearings
        self.SetHost()
        
        #running conditions
        self.Go = True
        atexit.register(self.Stop)
                
        #now run
        self.start()
        
    def run(self):
        """
        The while loop for watching the files
        """
        self.logger.info('RAPD_ADSC_Server::run')
            
        self.UpdateStatusDataserver()
        counter = 0
        while(self.Go):
            counter += 1
            if self.CheckMarcollect():
                mlines  = self.GetMarcollect()
                mparsed = self.ParseMarcollect(mlines)
                if mparsed:
                    self.marcollect_queue.appendleft(mparsed.copy())
                    #self.mar_dict = mparsed.copy()
                    #print self.mar_dict
                    #self.AddMarcollect(mparsed)
            for i in range(5):
                if self.CheckXFStatus():
                    xparsed = self.NewXFStatus()
                    if xparsed:
                        self.xf_status_queue.appendleft(xparsed.copy())
                    break 
                else:
                    time.sleep(0.1)
            if counter == 15:
                self.UpdateStatusDataserver()
                counter = 0
            if self.one_run:
                break
    def Stop(self):
        """
        Used to stop the loop
        """
        self.logger.debug('RAPD_ADSC_Server::Stop')
            
        self.Go = False
        
    def SetHost(self):
        """
        Use os.uname to set files to watch
        """
        self.logger.debug('RAPD_ADSC_Server::SetHost')
        
        #figure out which host we are on
        host = os.uname()[1]
        #now grab the file locations, beamline from settings
        if settings.has_key(host):
            self.marcollect,self.xf_status,self.beamline = settings[host]
        else:
            self.marcollect,self.xf_status,self.beamline = settings['default']
        
            
    """
    MySQL Methods
    """
    def Connect2SQL(self):
        """
        Connect to the database
        """
        self.logger.debug('RAPD_ADSC_Server::Connect2SQL')
        try:
            #self.connection  = MySQLdb.connect(host=self.db_host,db=self.db_name,user=self.db_user,passwd=self.db_password)
            self.connection  = MySQLdb.connect(host=secrets['db_host'],db=secrets['db_data_name'],user=secrets['db_user'],passwd=self.Decode(secrets['db_password']))
            self.cursor      = self.connection.cursor()
        except:
            pass
        
    def UpdateStatusDataserver(self):
        """
        Update rapd_data.status_dataserver so everyone knows we are alive 
        """
        self.logger.debug('UpdateStatusDataserver')
        try:
            self.cursor.execute('INSERT INTO status_dataserver (ip_address,beamline) VALUES (%s,%s) ON DUPLICATE KEY UPDATE timestamp=CURRENT_TIMESTAMP',(self.ip_address,self.beamline))
        except:
            self.logger.exception('Error in UpdateStatusDataserver')
            #try to reconnect
            try:
                self.Connect2SQL()
            except:
                self.logger.exception('Error in UpdateStatusDataserver - Cannot reconnect to MySQL Database')

    """
    MARCOLLECT METHODS
    """ 
    def GetMarcollectTime(self):
        """
        Returns modification time of marcollect 
        Used by XMLRPC server
        """
        return(self.mar_time)
    
    def GetMarcollectData(self):
        """
        Returns dict of marcollect
        """
        if (len(self.marcollect_queue) > 0):
            return(self.marcollect_queue.pop())
        else:
            return(False)
    
    def CheckMarcollect(self):
        """
        return True if marcollect has been changed, False if not
        """
        tries = 0
        while (tries < 5):
            try:
                statinfo = os.stat(self.marcollect)
                break
            except:
                if tries == 4:
                    return(False)
                tries += 1
                
        #the modification time has not changed
        if (self.mar_time == statinfo.st_mtime):
            return(False)
        #the file has changed
        else:
            self.mar_time = statinfo.st_mtime
            return(True)

    def GetMarcollect(self):
        """
        return contents of marcollect
        """
        self.logger.debug('RAPD_ADSC_Server::GetMarcollect')
        #copy the file to prevent conflicts with other programs
        os.system('cp '+self.marcollect+' ./tmp_marcollect')
        #read in the lines of the file
        in_lines = open('./tmp_marcollect','r').readlines()
        #remove the temporary file
        os.system('rm -f ./tmp_marcollect')
        return(in_lines)

    def ParseMarcollect(self,lines):
        """
        Parse the lines from the file marcollect and return a dict that
        is somewhat intelligible
        NB - only used with one line run-containing marcollect so far
        """
        self.logger.debug('RAPD_ADSC_Server::ParseMarcollect')
        self.logger.debug(lines)
        
        try:
            out_dict = { 'Runs' : {} }
            for i in range(len(lines)):
                sline = lines[i].split(':')
                if sline[0] == 'Directory':
                    if sline[1].strip().endswith('/'):
                        out_dict['Directory'] = sline[1].strip()[:-1]
                    else:
                        out_dict['Directory'] = sline[1].strip()
                elif sline[0] == 'Image_Prefix':
                    if sline[1].strip().endswith('_'):
                        out_dict['Image_Prefix'] = sline[1].strip()[:-1]
                    else:
                        out_dict['Image_Prefix'] = sline[1].strip()
                elif sline[0] == 'Mode':
                    out_dict['Mode'] = sline[1].strip()
                elif sline[0] == 'ADC':
                    out_dict['ADC'] = sline[1].strip()
                elif sline[0] == 'Anomalous':
                    out_dict['Anomalous'] = sline[1].strip()
                elif sline[0] == 'Anom_Wedge':
                    out_dict['Anom_Wedge'] = sline[1].strip()
                elif sline[0] == 'Compression':
                    out_dict['Compression'] = sline[1].strip()
                elif sline[0] == 'Binning':
                    out_dict['Binning'] = sline[1].strip()
                elif sline[0] == 'Comment':
                    out_dict['Comment'] = sline[1].strip()
                elif sline[0] == 'Beam_Center':
                    out_dict['Beam_Center'] = sline[1].strip()
                elif sline[0] == 'MAD':
                    out_dict['MAD'] = sline[1].strip()
                elif sline[0] == 'Energy to Use':
                    pass
    
                #handle the run lines 
                elif sline[0] == 'Run(s)':
                    run_num = 0
                    for j in range(i+1,len(lines)):
                        my_sline = lines[j].split()
                        if len(my_sline) > 0:
                            out_dict['Runs'][str(run_num)] = {'file_source' : 'adsc',
                                                         'Run'          : my_sline[0],
                                                         'Start'        : my_sline[1],
                                                         'Total'        : my_sline[2],
                                                         'Distance'     : my_sline[3],
                                                         '2-Theta'      : my_sline[4],
                                                         'Phi'          : my_sline[5],
                                                         'Kappa'        : my_sline[6],
                                                         'Omega'        : my_sline[7],
                                                         'Axis'         : my_sline[8],
                                                         'Width'        : my_sline[9],
                                                         'Time'         : my_sline[10],
                                                         'De-Zngr'      : my_sline[11],
                                                         'Directory'    : out_dict['Directory'],
                                                         'Image_Prefix' : out_dict['Image_Prefix'],
                                                         'Anomalous'    : 'No' }
                            run_num += 1
                            if 'Yes' in out_dict['Anomalous']:
                                out_dict['Runs'][str(run_num-1)]['Anomalous'] = 'Yes'
                                out_dict['Runs'][str(run_num)] = {'file_source' : 'adsc',
                                                             'Run'          : str(100+int(my_sline[0])),
                                                             'Start'        : my_sline[1],
                                                             'Total'        : my_sline[2],
                                                             'Distance'     : my_sline[3],
                                                             '2-Theta'      : my_sline[4],
                                                             'Phi'          : my_sline[5],
                                                             'Kappa'        : my_sline[6],
                                                             'Omega'        : my_sline[7],
                                                             'Axis'         : my_sline[8],
                                                             'Width'        : my_sline[9],
                                                             'Time'         : my_sline[10],
                                                             'De-Zngr'      : my_sline[11],
                                                             'Directory'    : out_dict['Directory'],
                                                             'Image_Prefix' : out_dict['Image_Prefix'],
                                                             'Anomalous'    : 'Yes'}
                                run_num += 1
            if not out_dict['MAD']:
                out_dict['MAD'] = 'No'
                
            self.logger.debug("Resulting dict")
            self.logger.debug(out_dict)            
            
            return(out_dict)
        
        except:
            self.logger.exception('Failure to parse marcollect - error in format?')
            return(False)
    
    def AddMarcollect(self,data,attempt=0):
        """
        Add a new marcollect to the MySQL database
        """
        self.logger.debug('RAPD_ADSC_Server::AddMarcollect %d' % attempt)
            
        if attempt > 2:
            self.logger.debug('FAILED TO ADD MARCOLLECT AFTER 3 TRIES - Giving Up!')
            return(False)
            
        #connect to the database
        try:
            self.mar_dict = data.copy()
            self.cursor.execute("""INSERT INTO run_status (adc,
                                                           anom_wedge,
                                                           anomalous,
                                                           beam_center,
                                                           binning,
                                                           comment,
                                                           compression,
                                                           directory,
                                                           image_prefix,
                                                           mad,
                                                           mode,
                                                           beamline) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                                           (data['ADC'], 
                                                            data['Anom_Wedge'], 
                                                            data['Anomalous'], 
                                                            data['Beam_Center'],
                                                            data['Binning'], 
                                                            data['Comment'], 
                                                            data['Compression'], 
                                                            data['Directory'],
                                                            data['Image_Prefix'], 
                                                            data['MAD'], 
                                                            data['Mode'],
                                                            self.beamline))
            self.connection.commit()            
        
        except _mysql_exceptions.IntegrityError , (errno, strerror):
            if errno == 1062:
                self.logger.exception('This run_status is already in the database')
                if self.beamline == 'T':
                    self.logger.warning(data)
                    try:
                        self.cursor.execute("""UPDATE run_status SET adc          = %s,
                                                                 anom_wedge   = %s,
                                                                 anomalous    = %s,
                                                                 beam_center  = %s,
                                                                 binning      = %s,
                                                                 comment      = %s,
                                                                 compression  = %s,
                                                                 directory    = %s,
                                                                 image_prefix = %s,
                                                                 mad          = %s,
                                                                 mode         = %s,
                                                                 beamline     = %s WHERE directory = %s AND image_prefix = %s""",
                                                           (data['ADC'], 
                                                            data['Anom_Wedge'], 
                                                            data['Anomalous'], 
                                                            data['Beam_Center'],
                                                            data['Binning'],
                                                            data['Comment'], 
                                                            data['Compression'], 
                                                            data['Directory'],
                                                            data['Image_Prefix'], 
                                                            data['MAD'], 
                                                            data['Mode'],
                                                            self.beamline,
                                                            data['Directory'],
                                                            data['Image_Prefix']))
                        self.connection.commit()  
                        self.logger.debug('Run Status entered')
                    except:
                        self.logger.exception("Exception in updating run_status")
            else:
                self.logger.exception('ERROR : unknown IntegrityError exception in Database::AddMarcollect')
        
        except _mysql_exceptions.OperationalError , (errno, strerror):
            if errno == 2006:
                self.logger.exception('Connection to MySQL database lost. Will attempt to reconnect.')
                self.Connect2SQL()
                self.AddMarcollect(data,attempt=attempt+1)
            else:
                self.logger.exception('ERROR : unknown OperationalError in Database::AddMarcollect')   
        except:
            self.logger.exception('ERROR : unknown exception in Database::AddMarCollect')
          
        #add the runs even if we have an error with adding the marcollect
        results = []
        for run in data['Runs'].keys():
            results.append(self.AddRun(data['Runs'][run]))
            
        if True in results:
            return(True)
        else:
            return(False)    
            
    def AddRun(self,run,attempt=0):
        """
        Add a new run to the MySQL database
        """
        self.logger.debug('RAPD_ADSC_Server::AddRun')
        
        if attempt > 2:
            self.logger.warning('FAILED TO ADD RUN AFTER 3 TRIES - Giving Up!')
            return(False)
        
        try:
            self.logger.debug("Adding run into database directory:%s image_prefix:%s run_number:%s" %(run['Directory'],run['Image_Prefix'],run['Run']))
            self.cursor.execute("""INSERT INTO runs (directory,
                                                     image_prefix,
                                                     run_number,
                                                     start,
                                                     total,
                                                     distance,
                                                     twotheta,
                                                     phi,
                                                     kappa,
                                                     omega,
                                                     axis,
                                                     width,
                                                     time,
                                                     de_zngr,
                                                     anomalous,
                                                     beamline) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                                     (run['Directory'], 
                                                      run['Image_Prefix'], 
                                                      run['Run'], 
                                                      run['Start'], 
                                                      run['Total'], 
                                                      run['Distance'],
                                                      run['2-Theta'], 
                                                      run['Phi'], 
                                                      run['Kappa'], 
                                                      run['Omega'], 
                                                      run['Axis'],
                                                      run['Width'], 
                                                      run['Time'], 
                                                      run['De-Zngr'],
                                                      run['Anomalous'],
                                                      self.beamline))
            self.connection.commit()
            return(True)
       
        except _mysql_exceptions.IntegrityError , (errno, strerror):
            if errno == 1062:
                self.logger.exception('Run is already in the database')
                if self.beamline == 'T':
                    self.logger.debug(run)
                    self.cursor.execute("""UPDATE runs SET directory    = %s,
                                                           image_prefix = %s,
                                                           run_number   = %s,
                                                           start        = %s,
                                                           total        = %s,
                                                           distance     = %s,
                                                           twotheta     = %s,
                                                           phi          = %s,
                                                           kappa        = %s,
                                                           omega        = %s,
                                                           axis         = %s,
                                                           width        = %s,
                                                           time         = %s,
                                                           de_zngr      = %s,
                                                           anomalous    = %s,
                                                           beamline     = %s WHERE directory = %s AND image_prefix = %s AND run_number = %s AND start = %s""",
                                                           (run['Directory'], 
                                                            run['Image_Prefix'], 
                                                            run['Run'], 
                                                            run['Start'], 
                                                            run['Total'], 
                                                            run['Distance'],
                                                            run['2-Theta'], 
                                                            run['Phi'], 
                                                            run['Kappa'], 
                                                            run['Omega'], 
                                                            run['Axis'],
                                                            run['Width'], 
                                                            run['Time'], 
                                                            run['De-Zngr'],
                                                            run['Anomalous'],
                                                            self.beamline,
                                                            run['Directory'], 
                                                            run['Image_Prefix'], 
                                                            run['Run'], 
                                                            run['Start']))
                    self.connection.commit()
                    self.logger.debug("Run entered")
            else:
                self.logger.exception('ERROR : unknown IntegrityError exception in RAPD_ADSC_Server::AddRun')
            return(False)
        
        except _mysql_exceptions.OperationalError , (errno, strerror):
            if errno == 2006:
                self.logger.exception('Connection to MySQL database lost. Will attempt to reconnect.')
                self.Connect2SQL()
                self.AddRun(run,attempt=attempt+1)
            else:
                self.logger.exception('ERROR : unknown OperationalError in RAPD_ADSC_Server::AddRun')   
            return(False)
        
        except:
            self.logger.exception('ERROR : unknown exception in RAPD_ADSC_Server::AddRun')
            return(False)

    """
    XF_STATUS METHODS
    """
    def GetXFStatusTime(self):
        """
        Returns modification time of xf_status 
        Used by XMLRPC server
        """
        return(self.xf_time)
    
    def GetXFStatusData(self):
        """
        Returns dict of xf_status
        """
        if (len(self.xf_status_queue) > 0):
            return(self.xf_status_queue.pop())
        else:
            return(False)
    
    def NewXFStatus(self):
        """
        Called if xf_status modification time is newer than the time in memory
        """
        #get the line of the xf_status
        xlines  = self.GetXFStatus()
        #parse the lines
        xparsed = self.ParseXFStatus(xlines)
        #if there are lines after parsing i.e. this is a real file, add the info to the 
        #database and then look at the image
        return(xparsed)            
    
    def GetLastImage(self):
        """
        Returns the last image as taken from xf_status
        """
        return(self.last_image)
    
    def CheckXFStatus(self):
        """
        return True if xf_status has been changed, False if not
        """
        tries = 0
        while tries < 5:
            try:
                statinfo = os.stat(self.xf_status)
                break
            except :
                if tries == 4:
                    return(False)
                tries += 1
                
        #the modification time has not changed
        if (self.xf_time == statinfo.st_mtime):
            return(False)
        #the file has changed
        else:
            self.xf_time = statinfo.st_mtime
            return(True)     
         
    def GetXFStatus(self):
        """
        return contents of xf_status
        """
        #copy the file to prevent conflicts with other programs
        os.system('cp '+self.xf_status+' ./tmp_xf_status')
        #read in the lines of the file
        in_lines = open('./tmp_xf_status','r').readlines()
        #remove the temporary file
        os.system('rm -f ./tmp_xf_status')
        return(in_lines)
    
    def ParseXFStatus(self,lines):
        """
        Parse the lines from the file xf_status and return a dict that
        is somewhat intelligible
        """
        self.logger.debug('RAPD_ADSC_Server::ParseXFStatus')
        
        out_dict = { 'adsc_number'  : '',
                     'image_name'   : '',
                     'directory'    : '',
                     'image_prefix' : '',
                     'run_number'   : '',
                     'image_number' : '',
                     'status'       : 'None'}
        try:
            for i in range(len(lines)):
                sline = lines[i].split()
                if len(sline) == 2:
                    if sline[1].strip() == '<none>':
                        self.logger.debug('xf_status empty')
                        out_dict = False  
                        break
                    else:
                        try:
                            out_dict['adsc_number'] = sline[0]
                            out_dict['image_name']   = sline[1]
                            #set this for retrieval
                            self.last_image = sline[1] 
                            out_dict['directory']    = os.path.dirname(sline[1])
                            out_dict['image_prefix'] = '_'.join(os.path.basename(sline[1]).split('_')[:-2])
                            out_dict['run_number']   = os.path.basename(sline[1]).split('_')[-2]
                            out_dict['image_number'] = sline[1].split('_')[-1].split('.')[0]
                            out_dict['status']       = 'SUCCESS'
                            break
                        except:
                            self.logger.exception('Exception in RAPD_ADSC_Server::ParseXFStatus %s' % lines[i])
                            out_dict = False
                            break
            return(out_dict)
        except:
            self.logger.exception('Failure to parse xf_status - error in format?')
            return(False)
    
    def AddXFStatus(self,data,attempt=0):
        """
        Add a new xf_status to the MySQL database
        Return True if the image is successfully added to the database
        """
        self.logger.debug('RAPD_ADSC_Server::AddXFStatus')
            
        if attempt > 2:
            self.logger.warning('FAILED TO ADD XF_STATUS AFTER 3 TRIES - Giving Up!')
            return(False)
                
        try:
            self.xf_dict = data.copy()
            self.cursor.execute("""INSERT INTO image_status (fullname,
                                                             directory,
                                                             image_prefix,
                                                             run_number,
                                                             adsc_number,
                                                             image_number,
                                                             beamline) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                                             (data['image_name'], 
                                                              data['directory'], 
                                                              data['image_prefix'],
                                                              data['run_number'], 
                                                              data['adsc_number'], 
                                                              data['image_number'],
                                                              self.beamline))
            self.connection.commit()
        
        except _mysql_exceptions.IntegrityError , (errno, strerror):
            if errno == 1062:
                self.logger.exception('xf_status is already in the database')
            else:
                self.logger.exception('ERROR : unknown IntegrityError exception in RAPD_ADSC_Server::AddXFStatus')
        
        except _mysql_exceptions.OperationalError , (errno, strerror):
            if errno == 2006:
                self.logger.exception('Connection to MySQL database lost. Will attempt to reconnect.')
                self.Connect2SQL()
                self.AddXFStatus(data,attempt=attempt+1)
            else:
                self.logger.exception('ERROR : unknown OperationalError in RAPD_ADSC_Server::AddXFStatus')
        
        except:
            self.logger.exception('ERROR : unknown exception in RAPD_ADSC_Server::AddXFStatus')

    def Decode(self,item):
        return(base64.b64decode(item))

if __name__ == '__main__':
    
    #create the watcher instance
    watcher = RAPD_ADSC_Server()  
      
    #create the server
    server = SimpleXMLRPCServer(("", 8001),logRequests=False)
    server.register_function(watcher.GetMarcollectTime)
    server.register_function(watcher.GetXFStatusTime)
    server.register_function(watcher.GetMarcollectData)
    server.register_function(watcher.GetXFStatusData)
    server.register_function(watcher.GetLastImage)
    server.serve_forever()
    
