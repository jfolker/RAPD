"""Site description for SERCAT ID beamline"""

__license__ = """
This file is part of RAPD

Copyright (C) 2016-2018 Cornell University
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

__created__ = "2016-01-28"
__maintainer__ = "Frank Murphy"
__email__ = "fmurphy@anl.gov"
__status__ = "Development"

# Standar imports
import sys

# RAPD imports
from utils.site import read_secrets

# Site
SITE = "SERCAT"

# Site IDs
# Should be UPPERCASE
# May be a string or list or tuple of strings
ID = ("SERCAT_ID", "SERCAT_BM")

# The secrets file - do not put in github repo!
SECRETS_FILE = "sites.secrets_sercat"

# Copy the secrets attribute to the local scope
# Do not remove unless you know what you are doing!
read_secrets(SECRETS_FILE, sys.modules[__name__])

# X-ray source characteristics
# Keyed to ID
BEAM_INFO = {
    "SERCAT_BM" : {
        # Flux of the beam
        "BEAM_FLUX":8E11,
        # Size of the beam in mm
        "BEAM_SIZE_X":0.05,
        "BEAM_SIZE_Y":0.02,
        # Shape of the beam - ellipse, rectangle
        "BEAM_SHAPE":"ellipse",
        # Shape of the attenuated beam - circle or rectangle
        "BEAM_APERTURE_SHAPE":"circle",
        # Gaussian description of the beam for raddose
        #"BEAM_GAUSS_X":0.03,
        #"BEAM_GAUSS_Y":0.01,
        # Beam center calibration
        "BEAM_CENTER_DATE":"2015-12-07",
        # Beamcenter equation coefficients (b, m1, m2, m3, m4, m5, m6)
        "BEAM_CENTER_X":(109.627,
                         0,
                         0,
                         0,
                         0,
                         0,
                         0),
        "BEAM_CENTER_Y":(114.037,
                         0,
                         0,
                         0,
                         0,
                         0,
                         0),
        # Detector information
        "DETECTOR_DISTANCE_MAX":1000.0,
        "DETECTOR_DISTANCE_MIN":100.0,
        "DETECTOR_TIME_MAX":5.0,
        "DETECTOR_TIME_MIN":0.5,
        # Diffractometer information
        "DIFFRACTOMETER_OSC_MAX":5.0,
        "DIFFRACTOMETER_OSC_MIN":0.5
    },
    "SERCAT_ID" : {
        # Flux of the beam
        "BEAM_FLUX":8E11,
        # Size of the beam in mm
        "BEAM_SIZE_X":0.05,
        "BEAM_SIZE_Y":0.02,
        # Shape of the beam - ellipse, rectangle
        "BEAM_SHAPE":"ellipse",
        # Shape of the attenuated beam - circle or rectangle
        "BEAM_APERTURE_SHAPE":"circle",
        # Gaussian description of the beam for raddose
        #"BEAM_GAUSS_X":0.03,
        #"BEAM_GAUSS_Y":0.01,
        # Beam center calibration
        "BEAM_CENTER_DATE":"2015-12-07",
        # Beamcenter equation coefficients (b, m1, m2, m3, m4, m5, m6)
        "BEAM_CENTER_X":(150.7,
                         0,
                         0,
                         0,
                         0,
                         0,
                         0),
        "BEAM_CENTER_Y":(144.75,
                         0,
                         0,
                         0,
                         0,
                         0,
                         0)
    }
}

# Logging
# Linux should be /var/log/
#LOGFILE_DIR = "/tmp/log"
LOGFILE_DIR = "/home/schuerjp/temp/log"
LOG_LEVEL = 50

# Control process settings
# Process is a singleton? The file to lock to. False if no locking.
CONTROL_LOCK_FILE = "/home/schuerjp/temp/lock/rapd_control.lock"

# Method RAPD uses to match data root dir to a user & session
#   manual -- the data_root_dir will be connected manually with a group/session
#   uid -- the image header information generated by RAPD will contain session and group info
SESSION_METHOD = "image_file"

# Methods RAPD uses to track groups
#   type
#     stat -- uses os.stat to determine attribute used
#   attribute
#     uid -- st_uid
GROUP_ID = ("stat", "uid", "uidNumber")
# GROUP_ID = {
#     "type":"stat",
#     "attribute":"uid",
#     "field":"uidNumber"
# }
# The field name in groups collection that matches the property described in GROUP_ID
#   uidNumber
GROUP_ID_FIELD = "uidNumber"

# Where files are exchanged between plugins and control
EXCHANGE_DIR = "/panfs/panfs0.localdomain/home/schuerjp/exchange_dir/"

# Control settings
# Database to use for control operations. Options: "mysql"
CONTROL_DATABASE = "mongodb"

# Redis databse
# Running in a cluster configuration - True || False
# CONTROL_REDIS_CLUSTER = False

# Detector settings
# Must have a file in detectors that is all lowercase of this string
DETECTOR = False
DETECTOR_SUFFIX = ""
# Keyed to ID
DETECTORS = {"SERCAT_ID":("SERCAT_DECTRIS_EIGER16M", ""),
             "SERCAT_BM":("SERCAT_RAYONIX_MX300", "")}

# Launcher Manager to sort out where to send jobs
LAUNCHER_MANAGER_LOCK_FILE = "/home/schuerjp/temp/lock/launcher_manager.lock"

# Launcher settings
LAUNCHER_LOCK_FILE = "/home/schuerjp/temp/lock/launcher.lock"

# Launcher to send jobs to
# The value should be the key of the launcher to select in LAUNCHER_SPECIFICATIONS
LAUNCHER_TARGET = 1

# Directories to look for rapd agents
RAPD_PLUGIN_DIRECTORIES = ("sites.plugins",
                           "plugins")
# Queried in order, so a echo/plugin.py in src/sites/plugins will override
# the same file in src/plugins

# Directories to look for launcher adapters
RAPD_LAUNCHER_ADAPTER_DIRECTORIES = ("launch.launcher_adapters",
                                     "sites.launcher_adapters")
# Queried in order, so a shell_simple.py in src/sites/launcher_adapters will override
# the same file in launch/launcher_adapters

# Cluster settings
CLUSTER_ADAPTER = "sites.cluster.sercat"
# Set to False if there is no cluster adapter

# Data gatherer settings
# The data gatherer for this site, in the src/sites/gatherers directory
#GATHERER = "sercat_id.py"
GATHERER = "sercat.py"
GATHERER_LOCK_FILE = "/home/schuerjp/temp/lock/gatherer.lock"

# Monitor for collected images
IMAGE_MONITOR = "monitors.image_monitors.redis_image_monitor"
# Redis databse
# Running in a cluster configuration - True || False
# IMAGE_MONITOR_REDIS_CLUSTER = CONTROL_REDIS_CLUSTER
# Images collected into following directories will be ignored
IMAGE_IGNORE_DIRECTORIES = ("/var/sergui",)
# Images collected containing the following string will be ignored
IMAGE_IGNORE_STRINGS = ("ignore", "blankmar300hs", "_r1_UR", "_r1_UL", "_r1_AR", "_r1_AL")
# So if image is not present, look in long term storage location.
#ALT_IMAGE_LOCATIONS = False

# If processing images in NFS shared RAMDISK with different path 
# than long-term storage that was passed in. Check if they exist.
ALT_IMAGE_LOCATION = False
# Name of class in detector file that runs as server.
# Set to False if not using server 
#ALT_IMAGE_SERVER_NAME = 'FileLocation'

# Monitor for collected run information
RUN_MONITOR = "monitors.run_monitors.redis_run_monitor"
# Expected time limit for a run to be collected in minutes (0 = forever)
RUN_WINDOW = 60
# Running in a cluster configuration - True || False
# RUN_MONITOR_REDIS_CLUSTER = CONTROL_REDIS_CLUSTER

# Cloud Settings
# The cloud monitor module
CLOUD_MONITOR = "cloud.rapd_cloud"
# Pause between checking the database for new cloud requests in seconds
CLOUD_INTERVAL = 10
# Directories to look for cloud handlers
CLOUD_HANDLER_DIRECTORIES = ("cloud.handlers", )

# For connecting to the site
SITE_ADAPTER = False
# Running in a cluster configuration - True || False
SITE_ADAPTER_REDIS_CLUSTER = False

# For connecting to the remote access system fr the site
REMOTE_ADAPTER = "sites.site_adapters.necat_remote"     # file name prefix for adapter in src/
# REMOTE_ADAPTER_REDIS_CLUSTER = CONTROL_REDIS_CLUSTER


##
## Aggregators
## Be extra careful when modifying
CONTROL_DATABASE_SETTINGS = {
    "CONTROL_DATABASE":CONTROL_DATABASE,
    "DATABASE_HOST":CONTROL_DATABASE_HOST,
    "DATABASE_PORT":CONTROL_DATABASE_PORT,
    "DATABASE_USER":CONTROL_DATABASE_USER,
    "DATABASE_PASSWORD":CONTROL_DATABASE_PASSWORD,
    # Connection can be 'pool' for database on single computer, or
    # 'sentinal' for high availability on redundant computers.
    "REDIS_CONNECTION":"pool",
    "REDIS_HOST":CONTROL_REDIS_HOST,
    "REDIS_PORT":CONTROL_REDIS_PORT,
    "REDIS_DB":CONTROL_REDIS_DB,
    "REDIS_SENTINEL_HOSTS":CONTROL_SENTINEL_HOSTS,
    "REDIS_MASTER_NAME":CONTROL_REDIS_MASTER_NAME,
}


LAUNCHER_SETTINGS = {
    # "LAUNCHER_REGISTER":LAUNCHER_REGISTER,
    "LAUNCHER_SPECIFICATIONS":LAUNCHER_SPECIFICATIONS,
    "LOCK_FILE":LAUNCHER_LOCK_FILE,
    "RAPD_LAUNCHER_ADAPTER_DIRECTORIES":RAPD_LAUNCHER_ADAPTER_DIRECTORIES
}

LAUNCH_SETTINGS = {
    "RAPD_PLUGIN_DIRECTORIES":RAPD_PLUGIN_DIRECTORIES,
    # "LAUNCHER_ADDRESS":(LAUNCHER_SPECIFICATIONS[LAUNCHER_TARGET]["ip_address"],
    #                     LAUNCHER_SPECIFICATIONS[LAUNCHER_TARGET]["port"])
    "LAUNCHER_SPECIFICATIONS":LAUNCHER_SPECIFICATIONS,
}

# BEAM_SETTINGS = {"BEAM_FLUX":BEAM_FLUX,
#                  "BEAM_SIZE_X":BEAM_SIZE_X,
#                  "BEAM_SIZE_Y":BEAM_SIZE_Y,
#                  "BEAM_SHAPE":BEAM_SHAPE,
#                  "BEAM_APERTURE_SHAPE":BEAM_APERTURE_SHAPE,
#                  "BEAM_GAUSS_X":BEAM_GAUSS_X,
#                  "BEAM_GAUSS_Y":BEAM_GAUSS_Y,
#                  "BEAM_CENTER_DATE":BEAM_CENTER_DATE,
#                  "BEAM_CENTER_X":BEAM_CENTER_X,
#                  "BEAM_CENTER_Y":BEAM_CENTER_Y}


IMAGE_MONITOR_SETTINGS = {"REDIS_HOST" : IMAGE_MONITOR_REDIS_HOST,
                          "REDIS_PORT" : IMAGE_MONITOR_REDIS_PORT,
                          #   "REDIS_CLUSTER" : IMAGE_MONITOR_REDIS_CLUSTER,
                          "SENTINEL_HOST" : IMAGE_MONITOR_SENTINEL_HOSTS,
                          "SENTINEL_PORT" : IMAGE_MONITOR_SENTINEL_PORT,
                          'REDIS_CONNECTION':"pool",
                          "REDIS_MASTER_NAME" : IMAGE_MONITOR_REDIS_MASTER_NAME,
                          "REDIS_SENTINEL_HOSTS" : IMAGE_MONITOR_SENTINEL_HOSTS,
                          }

RUN_MONITOR_SETTINGS = {"REDIS_HOST" : RUN_MONITOR_REDIS_HOST,
                        "REDIS_PORT" : RUN_MONITOR_REDIS_PORT,
                        # "REDIS_CLUSTER" : RUN_MONITOR_REDIS_CLUSTER,
                        "SENTINEL_HOST" : RUN_MONITOR_SENTINEL_HOSTS,
                        "SENTINEL_PORT" : RUN_MONITOR_SENTINEL_PORT,
                        "REDIS_CONNECTION":"pool",
                        "REDIS_SENTINEL_HOSTS" : RUN_MONITOR_SENTINEL_HOSTS,
                        "REDIS_MASTER_NAME" : RUN_MONITOR_REDIS_MASTER_NAME}

CLOUD_MONITOR_SETTINGS = {
    "CLOUD_HANDLER_DIRECTORIES" : CLOUD_HANDLER_DIRECTORIES,
    "DETECTOR_SUFFIX" : DETECTOR_SUFFIX,
    "UI_HOST" : UI_HOST,
    "UI_PORT" : UI_PORT,
    "UI_USER" : UI_USER,
    "UI_PASSWORD" : UI_PASSWORD,
    # "UPLOAD_DIR" : UPLOAD_DIR
    }

SITE_ADAPTER_SETTINGS = {"ID" : ID,
                         "REDIS_HOST" : SITE_ADAPTER_REDIS_HOST,
                         "REDIS_PORT" : SITE_ADAPTER_REDIS_PORT,
                         "REDIS_DB" : SITE_ADAPTER_REDIS_DB}

REMOTE_ADAPTER_SETTINGS = {"ID" : ID,
                           "MONGO_CONNECTION_STRING" : REMOTE_ADAPTER_MONGO_CONNECTION_STRING,
                        #    "REDIS_CLUSTER" : REMOTE_ADAPTER_REDIS_CLUSTER,
                           "SENTINEL_HOST" : REMOTE_ADAPTER_SENTINEL_HOSTS,
                           "SENTINEL_PORT" : REMOTE_ADAPTER_SENTINEL_PORT,
                           "REDIS_CONNECTION":"pool",
                           "REDIS_SENTINEL_HOSTS" : REMOTE_ADAPTER_SENTINEL_HOSTS,
                           "REDIS_MASTER_NAME" : REMOTE_ADAPTER_REDIS_MASTER_NAME,
                           "REDIS_HOST" : REMOTE_ADAPTER_REDIS_HOST,
                           "REDIS_PORT" : REMOTE_ADAPTER_REDIS_PORT}
