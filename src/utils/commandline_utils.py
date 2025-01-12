"""
Utilities for commandline running
"""

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

__created__ = "2016-11-28"
__maintainer__ = "Frank Murphy"
__email__ = "fmurphy@anl.gov"
__status__ = "Development"

# Standard imports
import argparse
import glob
import multiprocessing
import os
import pprint
import shutil
import sys
import time

# CCTBX Imports
from cctbx.sgtbx import space_group_symbols

# RAPD imports
import detectors.detector_utils as detector_utils
# import utils.log
# import utils.lock
import utils.convert_hdf5_cbf as convert_hdf5_cbf
import utils.site
import utils.spacegroup as spacegroup
# import utils.text as text

# The data processing parser - to be used by commandline RAPD processes
dp_parser = argparse.ArgumentParser(add_help=False)

# Verbosity
dp_parser.add_argument("-v", "--verbose",
                       action="store_true",
                       dest="verbose",
                       help="Enable verbose feedback in the terminal")

# No log file
dp_parser.add_argument("--nolog",
                       action="store_false",
                       dest="logging",
                       help="Do not create log file")

# No plotting in commandline
dp_parser.add_argument("--noplot",
                       action="store_false",
                       dest="show_plots",
                       help="Do not display plots in CLI")

# No color in terminal printing
dp_parser.add_argument("--color",
                       action="store_false",
                       dest="no_color",
                       help="Use colors in CLI")

# Test mode?
dp_parser.add_argument("-t", "--test",
                       action="store_true",
                       dest="test",
                       help="Run in test mode")

# Output JSON?
dp_parser.add_argument("--json",
                       action="store_true",
                       dest="json",
                       help="Output only final and full JSON")

# Set filedescriptor for JSON output
dp_parser.add_argument("--json-fd",
                       action="store",
                       dest="json_fd",
                       default=False,
                       help="Output json to a file descriptor. No need to also use --json, unless you want JSON on the terminal too.")

# Output progress updates?
dp_parser.add_argument("--progress",
                       action="store_true",
                       dest="progress",
                       help="Output progress updates to the terminal")

# Set filehandle for progress output
dp_parser.add_argument("--progress-fd",
                       action="store",
                       dest="progress_fd",
                       default=False,
                       help="Output progress updates to a file descriptor. No need to also use --progress, unless you want JSON on the terminal too.")

# The site
dp_parser.add_argument("-s", "--site",
                       action="store",
                       dest="site",
                       help="Define the site (ex. NECAT)")

# List possible sites
dp_parser.add_argument("-ls", "--listsites",
                       action="store_true",
                       dest="listsites",
                       help="List the available sites")

# The detector
dp_parser.add_argument("-d", "--detector",
                       action="store",
                       dest="detector",
                       help="Define the detector (ex. adsc_q315)")

# List possible detectors
dp_parser.add_argument("-ld", "--listdetectors",
                       action="store_true",
                       dest="listdetectors",
                       help="List the available detectors")

# Beam center
dp_parser.add_argument("-b", "--beamcenter",
                       action="store",
                       dest="beamcenter",
                       default=[False, False],
                       nargs=2,
                       type=float,
                       help="Define the beam center x,y")

# Spacegroup
dp_parser.add_argument("-sg", "--sg", "--spacegroup",
                       action="store",
                       dest="spacegroup",
                       default=False,
                       help="Input a spacegroup")

# Unit cell
dp_parser.add_argument("-u", "--unit", "--unitcell",
                       action="store",
                       dest="unitcell",
                       default=False,
                       nargs=6,
                       type=float,
                       help="Input a unit cell a b c alpha beta gamma")

# Sample type
dp_parser.add_argument("--sample_type",
                       action="store",
                       dest="sample_type",
                       default="protein",
                       choices=["protein", "dna", "rna", "peptide", "ribosome"],
                       help="The type of sample")

# Solvent fraction
dp_parser.add_argument("--solvent",
                       action="store",
                       dest="solvent",
                       default=0.55,
                       type=float,
                       help="Solvent fraction 0.0-1.0")

# Resolution low
dp_parser.add_argument("--lowres",
                       action="store",
                       dest="lowres",
                       default=0.0,
                       type=float,
                       help="Low resolution limit")

# Resolution hi
dp_parser.add_argument("--hires",
                       action="store",
                       dest="hires",
                       default=0.0,
                       type=float,
                       help="High resolution limit")

# Working directory
dp_parser.add_argument("--work_dir",
                       action="store",
                       dest="work_dir",
                       default=False,
                       help="Working directory")

# Number of processors to use
dp_parser.add_argument("--nproc",
                       action="store",
                       dest="nproc",
                       type=int,
                       default=multiprocessing.cpu_count(),
                       help="Number of processors to use. Defaults to the number of \
                             processors available")

# Use the cluster
dp_parser.add_argument("--cluster",
                       action="store_true",
                       dest="cluster_use",
                       help="Use cluster")

# Directory for exchanging files (used by some server installs)
dp_parser.add_argument("--exchange_dir",
                       action="store",
                       dest="exchange_dir",
                       help="Root directory for file excahnge between RAPD server entities")


# The rapd file generating parser - to be used by commandline RAPD processes
gf_parser = argparse.ArgumentParser(add_help=False)

# Verbosity
gf_parser.add_argument("-v", "--verbose",
                       action="store_true",
                       dest="verbose",
                       help="Enable verbose feedback")

# Test mode?
gf_parser.add_argument("-t", "--test",
                       action="store_true",
                       dest="test",
                       help="Run in test mode")

# Test mode?
gf_parser.add_argument("-f", "--force",
                       action="store_true",
                       dest="force",
                       help="Allow overwriting of files")

# Maintainer
gf_parser.add_argument("-m", "--maintainer",
                       action="store",
                       dest="maintainer",
                       default="Your name",
                       help="Maintainer's name")

# Maintainer's email
gf_parser.add_argument("-e", "--email",
                       action="store",
                       dest="email",
                       default="Your email",
                       help="Maintainer's email")

# Directory or files
gf_parser.add_argument(action="store",
                       dest="file",
                       nargs="?",
                       default=False,
                       help="Name of file to be generated")

def regularize_spacegroup(sg_in):
    """Standardize the input spacegroup to numeric form"""

    return space_group_symbols(sg_in).number()

def check_work_dir(target_dir, active=True, up=False):
    """
    Check if a directory exists, increment old versions if present and create an
    empty instance

    Arguments
    ---------
    target_dir - string directory to make
    active - boolean if True make and move directories, if False make no changes but return new
             directory name
    up - If True, newest directory will count up. If my_dir exists, new directory will be my_dir_1
         If False, old directories will be incremented, so if my_dir exists, my_dir will be moved
         to my_dir_1 and the new directory will be my_dir
    """

    # print "check_work_dir %s %s" % (target_dir, active)

    target_dir = os.path.abspath(target_dir)

    # Target dir exists
    if os.path.exists(target_dir):
        # Going up
        if up:
            # Look for the highest incremented directory
            i = 1
            while True:
                if os.path.exists(target_dir+"_%d" % i):
                    i += 1
                else:
                    break
            target_dir = target_dir + "_%d" % i
        # Everyone else is going up
        else:
            # If not active and not up - just return directory name
            if active:
                # Look for the highest incremented directory
                i = 1
                while True:
                    if os.path.exists(target_dir+"_%d" % i):
                        i += 1
                    else:
                        break

                # Move the present directories around
                for j in range(i, 0, -1):
                    k = j - 1
                    # Add a 1 to current target
                    if k == 0:
                        # print "Move %s to %s_1" % (target_dir, target_dir)
                        shutil.move(target_dir, target_dir+"_1")
                    # Move an already incremented directory higher
                    else:
                        # print "Move %s_%d to %s_%d" % (target_dir, k, target_dir, j)
                        shutil.move(target_dir+"_%d" % k, target_dir+"_%d" % j)

    # Now make the target directory
    if active:
        os.makedirs(target_dir)

    return target_dir

def print_sites(left_buffer=""):
    """
    Print out all the sites
    """
    sites = utils.site.get_site_files()

    for site in sites:
        print left_buffer + os.path.basename(site)

def print_detectors(left_buffer="", show_py=False):
    """
    Print out all the detectors
    """
    detectors = detector_utils.get_detector_files()

    for detector in detectors:
        if not show_py:
            detector_name = os.path.basename(detector).replace(".py", "")
        else:
            detector_name = os.path.basename(detector)

        print left_buffer + detector_name

def analyze_data_sources(sources,
                         mode="index",
                         start_image=False,
                         end_image=False,
                         hdf5_image_range=False,
                         hdf5_wedge_range=False,
                         timeout=1):
    """
    Return information on files or directory from input
    """
    # print "analyze_data_sources", sources

    return_data = {}

    if mode == "index":
        # If inputting an h5 dataset or single image
        if len(sources) == 1 and os.path.abspath(sources[0]).endswith(".h5"):
            converter = convert_hdf5_cbf.hdf5_to_cbf_converter(
                                master_file=os.path.abspath(sources[0]),
                                output_dir="cbf_files",
                                image_range=hdf5_image_range,
                                wedge_range=hdf5_wedge_range,
                                #overwrite=True,
                                verbose=False)
            converter.run()
            return_data["hdf5_files"] = [os.path.abspath(sources[0])]
            return_data["files"] = [os.path.abspath(f) for f in converter.output_images]

        else:
            prefix = False
            for source in sources:
                source_abspath = os.path.abspath(source)
                # print "  source_abspath:", source_abspath

                # Does file/dir exist?
                if os.path.exists(source_abspath):
                    if os.path.isdir(source_abspath):
                        pass
                    elif os.path.isfile(source_abspath):

                        # Are we dealing with hdf5 images
                        if source_abspath.endswith(".h5"):
                            # Needed for Labelit to have same root name to pairs of images.
                            if prefix == False:
                                prefix = convert_hdf5_cbf.get_prefix(source_abspath)
                            
                            if not "hdf5_files" in return_data:
                                return_data["hdf5_files"] = [source_abspath]
                            else:
                                return_data["hdf5_files"].append(source_abspath)

                            converter = convert_hdf5_cbf.hdf5_to_cbf_converter(
                                master_file=source_abspath,
                                output_dir="cbf_files",
                                #start_image=len(return_data["hdf5_files"]),
                                #end_image=len(return_data["hdf5_files"]),
                                renumber_image=len(return_data["hdf5_files"]),
                                prefix=prefix,
                                image_range='1',
                                overwrite=True,
                                verbose=False)
    
                            converter.run()
    
                            #source_abspath = os.path.abspath(converter.output_images[0])
                            source_abspath = os.path.abspath(converter.output_images[-1])
    
                        # 1st file of 1 or 2
                        if not "files" in return_data:
                            return_data["files"] = [source_abspath]
    
                        # 3rd file - error
                        elif len(return_data["files"]) > 1:
                            raise Exception("Up to two images can be submitted for indexing")
                        # 2nd file - presumably a pair
                        else:
                            # Same file twice
                            if source_abspath == return_data["files"][0]:
                                raise Exception("The same image has been submitted twice for indexing")
                            else:
                                return_data["files"].append(source_abspath)
                                break
    
                else:
                    raise Exception("%s does not exist" % source_abspath)

        return return_data

    elif mode == "integrate":

        # HDF5 file
        if sources.endswith(".h5"):

            source_abspath = os.path.abspath(sources)

            if not "hdf5_files" in return_data:
                return_data["hdf5_files"] = [source_abspath]
            else:
                return_data["hdf5_files"].append(source_abspath)

            #if not start_image:
            #    start_image = 1
            
            if start_image and end_image:
                image_range = '%s-%s'%(start_image, end_image)
            elif start_image and not end_image:
                image_range = '%s-end'%start_image
            elif not start_image and end_image:
                image_range = '1-%s'%end_image
            else:
                image_range = 'all'

            converter = convert_hdf5_cbf.hdf5_to_cbf_converter(
                master_file=source_abspath,
                output_dir="cbf_files",
                #prefix=prefix,
                #start_image=start_image,
                #end_image=end_image,
                image_range=image_range,
                overwrite=False,
                verbose=False)

            converter.run()

            return_data["data_files"] = converter.output_images

            return return_data

        # NOT HDF5
        else:

            template = sources

            # Establish the abspath
            full_path_template = os.path.abspath(template).replace("?", "#")

            # Grab a list of files
            # "?" as numbers that increment
            # "#" as numbers that increment
            depth = full_path_template.count("#")
            number_format = "%0"+str(depth)+"d"
            # print number_format

            if start_image:
                first_file = full_path_template.replace("#"*depth, number_format % start_image, 1)
                # Mark as needing to look to make sure image number is in range
                in_range = False
            else:
                # No need to worry about the image number
                in_range = True

            if end_image:
                last_file = full_path_template.replace("#"*depth, number_format % end_image, 1)

            return_data["data_files"] = []
            full_path_template = full_path_template.replace("?", "[0-9]").replace("#", "[0-9]")
            start_time = time.time()

            while (time.time() - start_time) < timeout:
                # sys.stdout.write(".")
                # sys.stdout.flush()
                # Look at FS for data files
                data_files = glob.glob(full_path_template)
                data_files.sort()

                # Go through the data files found
                for data_file in data_files:
                    # Images are in the range for images of interest
                    if in_range:
                        return_data["data_files"].append(data_file)
                        if end_image:
                            if last_file == data_file:
                                break
                    else:
                        if first_file == data_file:
                            in_range = True
                            # print data_file
                            return_data["data_files"].append(data_file)

                # Have some files - break the while loop
                if return_data["data_files"]:
                    break
                else:
                    time.sleep(0.1)

            # Sort into order
            return_data["data_files"].sort()

            if len(return_data["data_files"]) == 0:
                raise Exception("Unable to find files for the template: %s" \
                                % template)

            return return_data

if __name__ == "__main__":

    #print "commandline_utils.py"
    os.chdir('/gpfs6/users/necat/Jon/RAPD_test/Output')
    s = ['/gpfs6/users/necat/Jon/RAPD_test/Images/LSCAT/Ni-edge-n59d-kda28cl36cf57h.001_master.h5']
    analyze_data_sources(s, 'index', )

    """
    parser = argparse.ArgumentParser(parents=[dp_parser],
                                     description="Testing")
    returned_args = parser.parse_args()
    print "\nVariables:"
    print "%20s  %-10s" % ("var", "val")
    print "%20s  %-10s" % ("=======", "=======")
    for pair in returned_args._get_kwargs():
        print "%20s  %-10s" % pair


    print "\nSites:"
    print_sites(left_buffer="  ")
    """
