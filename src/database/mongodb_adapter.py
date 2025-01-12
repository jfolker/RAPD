"""
This is an adapter for RAPD to connect to the results database, when it is a
MongoDB instance
"""

__license__ = """
This file is part of RAPD

Copyright (C) 2009-2018, Cornell University
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
__created__ = "2016-05-31"
__maintainer__ = "Frank Murphy"
__email__ = "fmurphy@anl.gov"
__status__ = "Production"

"""
To run a MongoDB instance in docker:
sudo docker run --name mongodb -p 27017:27017 -d mongo:3.4
"""

# Standard imports
import base64
import bson.errors
from bson.objectid import ObjectId
import copy
import datetime
import logging
import os
from pprint import pprint
# import shutil
import threading

import pymongo
import gridfs

from utils.text import json

CONNECTION_ATTEMPTS = 30

#
# Utility functions
#
def get_object_id(value):
    """Attempts to wrap ObjectIds to something reasonable"""
    return_val = None

    # print "get_object_id", value

    try:
        return_val = ObjectId(value)
    except (bson.errors.InvalidId, TypeError) as error:
        if value == "None":
            return_val = None
        elif value == "False":
            return_val = False
        elif value == "True":
            return_val = True
        else:
            return_val = value

    return return_val

def traverse_and_objectidify(input_object):
    """Traverses an object and looks for object_ids to turn into ObjectIds"""

    print "traverse_and_objectidify"
    pprint(input_object)

    if isinstance(input_object, dict):
        for key, val in input_object.iteritems():
            if isinstance(val, str):
                if isinstance(key, str):
                    if "_id" in key:
                        input_object[key] = get_object_id(val)
            elif isinstance(val, dict):
                input_object[key] = traverse_and_objectidify(val)

    return input_object

class Database(object):
    """
    Provides connection to MongoDB for Model.
    """

    client = None

    def __init__(self,
                 host=None,
                 port=27017,
                 user=None,
                 password=None,
                 settings=None,
                 string=None):

        """
        Initialize the adapter

        Keyword arguments
        host --
        port --
        user --
        password --
        settings --
        """

        # Get the logger
        self.logger = logging.getLogger("RAPDLogger")

        # Store passed in variables
        # Using the settings "shorthand"
        if settings:
            #self.db_host = settings["DATABASE_HOST"]
            #self.db_port = settings["DATABASE_PORT"]
            #self.db_user = settings["DATABASE_USER"]
            #self.db_password = settings["DATABASE_PASSWORD"]
            #elf.db_string = settings["DATABASE_STRING"]
            #self.db_host = settings["DATABASE_HOST"]
            #self.db_port = settings["DATABASE_PORT"]
            self.db_host = settings.get("DATABASE_HOST", host)
            self.db_port = settings.get("DATABASE_PORT", port)
            self.db_user = settings.get("DATABASE_USER", user)
            self.db_password = settings.get("DATABASE_PASSWORD", password)
            self.db_string = settings.get("DATABASE_STRING", string)
            
            # self.db_data_name = settings["DATABASE_NAME_DATA"]
            # self.db_users_name = settings["DATABASE_NAME_USERS"]
            # self.db_cloud_name = settings["DATABASE_NAME_CLOUD"]
        # Olde Style
        else:
            self.db_host = host
            self.db_port = port
            self.db_user = user
            self.db_password = password
            self.db_string = string
            # self.db_data_name = data_name
            # self.db_users_name = users_name
            # self.db_cloud_name = cloud_name

        # A lock for troublesome fast-acting data entry
        self.LOCK = threading.Lock()

    ############################################################################
    # Functions for connecting to the database                                 #
    ############################################################################
    def get_db_connection(self, read_only=False):
        """
        Returns a connection and cursor for interaction with the database.
        """

        if read_only:
            read_preference = "secondaryPreferred"
        else:
            read_preference = "primary"

        # No client - then connect
        if not self.client:
            self.logger.debug("Connecting to MongDB at %s:%d", self.db_host, self.db_port)
            # Connect
            if self.db_string:
                # When using login and pass.
                self.client = pymongo.MongoClient(self.db_string, 
                                                  readPreference=read_preference,
                                                  )
            else:
                # Not using user/password for now
                self.client = pymongo.MongoClient(host=self.db_host,
                                                  port=self.db_port,
                                                  readPreference=read_preference,
                                                  )

        # Get the db
        db = self.client.rapd

        return db

    ############################################################################
    # Functions for groups                                                     #
    ############################################################################
    def get_group(self, value, field="_id", just_id=False):
        """
        Returns a dict from the database when queried with value and field.

        value - the value for the search
        field - the field to be queried
        """

        self.logger.debug(value, field)

        # No value, no query
        if not value:
            return False

        # If it should be an ObjectId, cast it to one
        _value = get_object_id(value)
        # try:
        #     _value = ObjectId(value)
        # except bson.errors.InvalidId:
        #     _value = value

        # Get connection to database
        db = self.get_db_connection()

        # Query
        db_return = db.groups.find_one({field:_value})

        # Query and return, transform _id to string
        if just_id:
            if db_return:
                db_return = str(db_return["_id"])

        return db_return

    ############################################################################
    # Functions for sessions & users                                           #
    ############################################################################
    def get_session_id(self, data_root_dir):
        """
        Get the session _id for the input information. The entry will be made it does not yet exist.
        The data_root_dir must be input for this to work.

        Keyword arguments
        data_root_dir -- root of data for a session (ex. /raw/ID_16_05_25_uga_jjc)
        group_name -- name for a group (ex. uga_jjc) (default = None)
        session_name -- name for a session (ex. ID_16_05_25_uga_jjc) (default = None)
        """

        self.logger.debug("get_session_id data_root_dir: %s" % data_root_dir)

        # Connect
        db = self.get_db_connection()

        # Retrieve the session id
        session_id = db.sessions.find_one({"data_root_dir":data_root_dir}, {"_id":1})

        if session_id:
            session_id = str(session_id.get("_id", False))

        return str(session_id)

    def create_session(self,
                       data_root_dir,
                       group=None,
                       session_type="mx",
                       site=None):
        """
        Get the session _id for the input information. The entry will be made it does not yet exist.
        The data_root_dir must be input for this to work.

        Keyword arguments
        data_root_dir -- root of data for a session (ex. /raw/ID_16_05_25_uga_jjc)
        group_id -- id for a group (default = None)
        session_name -- name for a session (ex. ID_16_05_25_uga_jjc) (default = None)
        """

        self.logger.debug("create_session")

        # Logging
        self.logger.debug("data_root_dir: %s", data_root_dir)

        # Connect
        db = self.get_db_connection()

        # Make sure the group_id is an ObjectId
        # If it should be an ObjectId, cast it to one
        _group = get_object_id(group)
        # try:
        #     group = ObjectId(group)
        # except bson.errors.InvalidId:
        #     pass

        # Insert into the database
        result = db.sessions.insert_one({"data_root_dir": data_root_dir,
                                         "group":_group,
                                         "site":site,
                                         "type":session_type,
                                         "timestamp": datetime.datetime.utcnow()})

        return str(result.inserted_id)


    ############################################################################
    # Functions for images                                                     #
    ############################################################################
    def add_image(self, data, return_type="id"):
        """
        Add new image to the MySQL database.

        Keyword arguments
        data -- dict with all the requisite parts
        return_type -- "boolean", "id", or "dict" (default = "id")
        """

        db = self.get_db_connection()

        # Add timestamp
        data_copy = copy.deepcopy(data)
        data_copy["timestamp"] = datetime.datetime.utcnow()

        # Insert into db
        try:
            result = db.images.insert_one(data_copy)
        # Image already entered
        except pymongo.errors.DuplicateKeyError:
            return False

        # Return the requested type
        if return_type == "boolean":
            return True
        elif return_type == "id":
            return str(result.inserted_id)
        elif return_type == "dict":
            result_dict = db.find_one({"_id":result.inserted_id})
            result_dict["_id"] = str(result_dict["_id"])
            return result_dict

    def get_image_by_image_id(self, image_id):
        """
        Returns a dict from the database when queried with image_id.

        image_id - the _id for the images collection. May be a string or ObjectId
        """

        self.logger.debug(image_id)

        # Make sure we are querying by ObjectId
        _image_id = get_object_id(image_id)

        # Get connection to database
        db = self.get_db_connection()

        # Query and return, transform _id to string
        return_dict = db.images.find_one({"_id":_image_id})
        return_dict["_id"] = str(return_dict["_id"])
        return db.images.find_one({"_id":_image_id})

    ############################################################################
    # Functions for results                                                    #
    ############################################################################
    def save_plugin_result(self, plugin_result):
        """
        Add a result from a plugin

        Keyword argument
        plugin_result -- dict of information from plugin - must have a process key pointing to entry
        """

        self.logger.debug("save_plugin_result %s:%s", plugin_result["plugin"]["type"], plugin_result["process"])

        if plugin_result["plugin"]["type"] in ("PDBQUERY",):
            #self.logger.debug(plugin_result)
            pass

        # Connect to the database
        db = self.get_db_connection()
        grid_fs = gridfs.GridFS(db)
        grid_bucket = gridfs.GridFSBucket(db)

        # Clear _id from plugin_result
        if plugin_result.get("_id"):
            del plugin_result["_id"]

        # Add the current timestamp to the plugin_result
        now = datetime.datetime.utcnow()
        plugin_result["timestamp"] = now

        # Make sure we are all ObjectIds - _ids in process dict
        for key, val in plugin_result["process"].iteritems():
            if "_id" in key:
                plugin_result["process"][key] = get_object_id(val)

        # The coordinating result_id (_id of results collection & process.result_id)
        _result_id = plugin_result["process"].get("result_id")

        #
        # Handle any file storage
        #
        def remove_files_from_db(files, result_id, file_type):
            """Remove old files from the db"""

            self.logger.debug("remove_files_from_db files:%s results_id:%s file_type:%s", files, result_id, file_type)

            # Cycle through file list
            for file_to_remove in files:

                # Find files to remove
                files_in_database = db.fs.files.find({"metadata.result_id":result_id,
                                                      "metadata.file_type":file_type,
                                                      "metadata.description":file_to_remove.get("description")})
                # self.logger.debug("Looking for %s", {"metadata.result_id":result_id,
                #                                      "metadata.file_type":file_type,
                #                                      "metadata.description":file_to_remove.get("description")})
                
                # Remove them
                for file_in_database in files_in_database:

                    # self.logger.debug("file_in_database: %s", file_in_database)
                    # self.logger.debug(">>> %s %s", file_in_database["metadata"]["hash"], file_to_remove["hash"])

                    # Remove if hashes don't match
                    if file_in_database["metadata"]["hash"] != file_to_remove["hash"]:
                        self.logger.debug("Removing file with _id:%s", file_to_remove["_id"])
                        grid_bucket.delete(file_in_database["_id"])

        def add_raw_file_to_db(path, metadata=None, replace=False):
            """Add files to MongoDB"""

            self.logger.debug("add_raw_file_to_db path:%s metadata:%s", path, metadata)

            # See if we already have this file
            file_in_database = db.fs.files.find_one({"metadata.hash":metadata["hash"]})

            # File already saved
            if file_in_database:
                # Overwrite
                if replace:
                    self.logger.debug("Overwriting file")
                    # Open the path
                    with open(path, "r") as input_object:
                        file_id = grid_bucket.upload_from_stream(filename=os.path.basename(path),
                                                                 source=input_object,
                                                                 metadata=metadata)
                # Do not overwrite
                else:
                    self.logger.debug("Not overwriting file")
                    file_id = file_in_database["_id"]
            # New file
            else:
                self.logger.debug("Writing new file")
                # Open the path
                with open(path, "r") as input_object:
                    file_id = grid_bucket.upload_from_stream(filename=os.path.basename(path),
                                                             source=input_object,
                                                             metadata=metadata)
            
            return file_id

        def add_archive_file_to_db(path, metadata=None, replace=False):
            """Add archive files to MongoDB - for use with client download"""
            
            self.logger.debug("add_archive_file_to_db path:%s metadata:%s", path, metadata)
            
            # See if we already have this file
            file_in_database = db.fs.files.find_one({"metadata.hash":metadata["hash"]})

            # File already saved
            if file_in_database:
                # Overwrite
                if replace:
                    self.logger.debug("Overwriting file")
                    # Encode file in base64
                    b64_encoded = base64.b64encode(open(path, "r").read())
                    # Save to MongoDB
                    file_id = grid_bucket.upload_from_stream(filename=os.path.basename(path),
                                                             source=b64_encoded,
                                                             metadata=metadata)
                # Do not overwrite
                else:
                    self.logger.debug("Not overwriting file")
                    file_id = file_in_database["_id"]
            # New file
            else:
                self.logger.debug("Writing new file")
                # Encode file in base64
                b64_encoded = base64.b64encode(open(path, "r").read())
                # Save to MongoDB
                file_id = grid_bucket.upload_from_stream(filename=os.path.basename(path),
                                                         source=b64_encoded,
                                                         metadata=metadata)

            return file_id

        add_funcs = {
            "archive_files":add_archive_file_to_db,
            "data_produced":add_raw_file_to_db,
            "for_display":add_raw_file_to_db
        }

        for file_type in ("archive_files", "data_produced", "for_display"):
            self.logger.debug("Looking for %s", file_type)
            if plugin_result["results"].get(file_type, False):

                self.logger.debug("Have %s", file_type)
                self.logger.debug(plugin_result["results"].get(file_type))

                # Erase old files
                remove_files_from_db(files=plugin_result["results"].get(file_type),
                                     result_id=_result_id,
                                     file_type=file_type)

                # Save the new
                for index in range(len(plugin_result["results"].get(file_type, []))):
                    
                    self.logger.debug("Saving the %d file", index)

                    # The file to save
                    data = plugin_result["results"].get(file_type, [])[index]
                    self.logger.debug(data)

                    # File exists - save it
                    if os.path.exists(data["path"]):

                        _file = data["path"]

                        self.logger.debug("Saving %s", _file)

                        # Upload the file to MongoDB
                        grid_id = add_funcs[file_type](path=_file,
                                                       metadata={"description":data.get("description", "archive"),
                                                                 "hash":data.get("hash"),
                                                                 "result_id":_result_id,
                                                                 "file_type":file_type})

                        self.logger.debug("Saved %s", grid_id)

                        # This _id is important
                        plugin_result["results"][file_type][index]["_id"] = grid_id

                        # Remove the file from the system
                        os.remove(_file)

                        # Create a nicer path now that the original file is gone
                        plugin_result["results"][file_type][index]["path"] = os.path.basename(_file)

                    # File doesn't exist
                    else:
                        plugin_result["results"][file_type][index]["_id"] = None



        #
        # Add to plugin-specific results
        #
        collection_name = ("%s_%s_results" % (plugin_result["plugin"]["data_type"],
                                              plugin_result["plugin"]["type"])).lower()
        self.logger.debug("Updating the %s collection process.result_id: %s",
                          collection_name,
                          _result_id)

        # Debugging call to query db
        # debug_result = db[collection_name].find_one({"process.result_id":_result_id})
        # self.logger.debug("Found previous plugin result %s" % debug_result._id)

        # Update the plugin-specific table
        result1 = db[collection_name].update_one(
            {"process.result_id":_result_id},
            {"$set":plugin_result},
            upsert=True)

        # Get the _id from updated entry
        if result1.raw_result.get("updatedExisting", False):
            plugin_result_id = db[collection_name].find_one(
                {"process.result_id":_result_id},
                {"_id":1})["_id"]
            self.logger.debug("%s _id from updatedExisting %s", collection_name, plugin_result_id)
        # upsert
        else:
            plugin_result_id = result1.upserted_id
            self.logger.debug("%s _id  from upserting %s", collection_name, plugin_result_id)
        # Add _id to plugin_result
        plugin_result["_id"] = get_object_id(plugin_result_id)

        #
        # Update results collection
        #
        result2 = db.results.update_one(
            {"_id":_result_id},
            {"$set":{
                "data_type":plugin_result["plugin"]["data_type"],
                "parent_id":plugin_result["process"].get("parent_id", False),
                "plugin_id":plugin_result["plugin"]["id"],
                "plugin_type":plugin_result["plugin"]["type"],
                "plugin_version":plugin_result["plugin"]["version"],
                "repr":plugin_result["process"].get("repr", "Unknown"),
                "result_id":get_object_id(plugin_result_id),
                "session_id":get_object_id(plugin_result["process"]["session_id"]),
                "status":plugin_result["process"].get("status", 0),
                "timestamp":now,
                }
            },
            upsert=True)

        # Get the _id from updated entry in results
        # Upserted
        if result2.upserted_id:
            result_id = result2.upserted_id

        # Modified
        else:
            result_id = db.results.find_one(
                {"result_id":get_object_id(plugin_result_id)},
                {"_id":1})["_id"]

        # Update parent processes
        if plugin_result.get("process", {}).get("parent_id", False):
            self.updateParentProcess(plugin_result)

        # Update the session last_process field
        db.sessions.update_one(
            {"_id":get_object_id(plugin_result["process"]["session_id"])},
            {"$set": {
                "last_process": now
            }}
        )

        # Return the _ids for the two collections
        return {"plugin_results_id":str(plugin_result_id),
                "result_id":str(result_id)}

    # def getArrayStats(self, in_array, mode="float"):
    #     """
    #     return the max,min,mean and std_dev of an input array
    #     """
    #     self.logger.debug('Database::getArrayStats')
    #
    #     if (mode == 'float'):
    #         narray = numpy.array(in_array, dtype=float)
    #
    #     try:
    #         return(narray.max(), narray.min(), narray.mean(), narray.std())
    #     except:
    #         return(0, 0, 0, 0)

    def updateParentProcess(self, plugin_result):
        """
        Update a parent process with the result now passed in

        Keyword arguments
        plugin_result -- dict of information from plugin
        """

        self.logger.debug("updateParentProcess")

        # Get connection to database
        db = self.get_db_connection()

        # Derive parent collection
        parent_data = plugin_result.get("process").get("parent")
        parent_collection = (parent_data.get('data_type')+"_"+parent_data.get('type')+"_results").lower()
        parent_result_id = plugin_result.get("process").get("parent_id")

        # Derive document key
        child_key = ("results."+plugin_result.get("plugin").get("type")).lower()

        # Update the parent
        db[parent_collection].update_one({"process.result_id":parent_result_id},
                                         {"$set":{
                                             child_key:plugin_result["_id"]
                                         }})

    ############################################################################
    # Functions for runs                                                       #
    ############################################################################
    def add_run(self, run_data, return_type="id"):
        """
        Add new run to the MySQL database.

        Keyword arguments
        data -- dict with all the requisite parts
        return_type -- "boolean", "id", or "dict" (default = "id")
        """

        self.logger.debug(run_data)

        # Add timestamp to the run_data
        run_data.update({"timestamp":datetime.datetime.utcnow()})

        db = self.get_db_connection()

        try:
            # Insert into db
            result = db.runs.insert_one(run_data)

            self.logger.debug(result.inserted_id)

            # Return the requested type
            if return_type == "boolean":
                return True
            elif return_type == "id":
                return str(result.inserted_id)
            elif return_type == "dict":
                result_dict = db.find_one({"_id":result.inserted_id})
                result_dict["_id"] = str(result_dict["_id"])
                return result_dict

        # Run already entered
        except pymongo.errors.DuplicateKeyError:
            return False

    def get_run(self,
                run_data=None,
                minutes=0,
                order="descending",
                return_type="boolean"):
        """
        Return information for runs that fit the data within the last minutes window. If minutes=0,
        no time limit. The return will either be a boolean, or a list of results.

        Match is performed on the directory, prefix, starting image number and
        total number of images.

        Keyword arguments
        run_data -- dict of run information (default None)
        minutes -- time window to look back into the data (default 0)
        order -- the order in which to sort the results, must be None, descending
                 or ascending (default descending)
        return_type -- "boolean", "id", "dict" (default = "boolean")
        """

        self.logger.debug("run_data:%s minutes:%d", run_data, minutes)

        # Get connection to database
        db = self.get_db_connection()

        # Order
        if order == "descending":
            order_param = -1
        elif order == "ascending":
            order_param = 1
        elif order == None:
            order_param = -1
        else:
            raise Exception("get_run_data order argument must be None, ascending, or descending")

        # Projection determined by return_type
        if return_type in ("boolean", "id"):
            projection = {"_id":1}
        else:
            projection = {}

        # Search parameters
        query = {"site_tag":run_data.get("site_tag", None),
                 "directory":run_data.get("directory", None),
                 "image_prefix":run_data.get("image_prefix", None),
                 "run_number":run_data.get("run_number", None),
                 "start_image_number":run_data.get("start_image_number", None),
                 "number_images":run_data.get("number_images", None)}

        # Limit to a time window
        if minutes != 0:
            time_limit = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
            query.update({"timestamp":{"$lt":time_limit}})

        # self.logger.debug(query)
        # self.logger.debug(projection)
        # self.logger.debug(order_param)

        results = db.runs.find(query, projection).sort("file_ctime", order_param)

        # self.logger.debug("results.count() %d", results.count())

        # If no return, return a False
        if results.count() == 0:
            return False
        else:
            if return_type == "boolean":
                # self.logger.debug("Returning True")
                return True
            else:
                return results

    def query_in_run(self,
                     site_tag,
                     directory,
                     image_prefix,
                     run_number,
                     image_number,
                     minutes=0,
                     order="descending",
                     return_type="boolean"):
        """
        Return True/False or with list of data depending on whether the image information could
        correspond to a run stored in the database.

        Depending on the return_type, return could be True/False, a list of dicts, or a list of ids.

        Keyword arguments
        site_tag -- string describing site (default None)
        directory -- where the image is located
        image_prefix -- the image prefix
        run_number -- number for the run
        image_number -- number for the image
        minutes -- time window to look back into the data (default 0)
        return_type -- "boolean", "id", "dict" (default = "boolean")
        """

        # self.logger.debug("query_in_run")

        # Order
        if order in ("descending", None):
            order_param = -1
        elif order == "ascending":
            order_param = 1
        else:
            raise Exception("get_run_data order argument must be None, ascending, or descending")

        # Get connection to database
        db = self.get_db_connection()

        # Search parameters
        query = {"site_tag":site_tag,
                 "directory":directory,
                 "image_prefix":image_prefix,
                 "run_number":run_number,
                 "start_image_number":{"$lte":image_number}}

        # Limit to a time window
        if minutes != 0:
            time_limit = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
            query.update({"timestamp":{"$lt":time_limit}})

        # Projection determined by return_type
        if return_type in ("boolean", "id"):
            projection = {"_id":1, "start_image_number":1, "number_images":1}
        else:
            projection = {}

        # self.logger.debug(query)
        # self.logger.debug(projection)
        # self.logger.debug(order_param)

        results = db.runs.find(query).sort("file_ctime", order_param)
        # self.logger.debug(results.count())

        # Now filter for image_number inclusion
        filtered_results = []
        for result in results:
            # self.logger.debug(result)
            if image_number <= (result["start_image_number"]+result["number_images"]+1):
                filtered_results.append(result)

        # If no return, return a False
        if len(filtered_results) == 0:
            # self.logger.debug("Returning False")
            return False
        else:
            # boolean
            if return_type == "boolean":
                return True
            elif return_type == "dict":
                for result in filtered_results:
                    result["_id"] = str(result["_id"])
                return filtered_results
            elif return_type == "id":
                result_ids = []
                for result in filtered_results:
                    result_ids.append(str(result["_id"]))
                return result_ids

    def retrieve_file(self, result_id=False, description=False, hash=False):
        """Retrieve & return a file from gridFS"""
        
        print "retrieve_file result_id=%s description=%s hash=%s" % (result_id, description, hash)

        self.logger.debug("retrieve_file result_id=%s description=%s hash=%s", result_id, description, hash)

        # Connect to the database
        db = self.get_db_connection(read_only=True)
        grid_fs = gridfs.GridFS(db)
        grid_bucket = gridfs.GridFSBucket(db)

        if hash:
            query = {"metadata.hash":hash}
        elif result_id and description:
            query = {"metadata.result_id":result_id, "metadata.description":description}
        else:
            raise Exception("Unable to query - not enough input data")

        # Query for the _id in the fs.files collection
        entry = db.fs.files.find_one(query)
        files_id = entry["_id"]
        
        # Grab the file
        grid_out = grid_bucket.open_download_stream(files_id)
        contents = grid_out.read()

        return (entry, contents)




#
# Utility functions
#
# def get_object_id(value):
#     """Attempts to wrap ObjectIds to something reasonable"""
#     return_val = None
#     try:
#         return_val = ObjectId(value)
#     except bson.errors.InvalidId:
#         if value == "None":
#             return_val = None
#         elif value == "False":
#             return_val = False
#         elif value == "True":
#             return_val = True
#         else:
#             pass
#     return return_val

if __name__ == "__main__":

    print "rapd_mongodb_adapter.py.__main__"

    test_dict = {
        "_id":"59e627aa799305396a42f1fc",
        "fake_id":"frank",
        "process":{
            "my_id":"59e627aa799305396a42f1fc",
            "not":"not an id",
            "third_shell": {
                "hidden_id":"59e627aa799305396a42f1fc",
            }
        }
    }

    pprint(test_dict)
    print "\n"
    res_dict = traverse_and_objectidify(test_dict)
    print("\n")
    pprint(res_dict)
