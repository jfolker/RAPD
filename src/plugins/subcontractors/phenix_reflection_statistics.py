"""Methiods for running BEST"""

"""
This file is part of RAPD

Copyright (C) 2017, Cornell University
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

__created__ = "2018-09-17"
__maintainer__ = "Frank Murphy"
__email__ = "fmurphy@anl.gov"
__status__ = "Development"

# Standard imports
# import argparse
# import from collections import OrderedDict
# import datetime
# import glob
# import json
# import logging
import math
# import multiprocessing
# import os
from pprint import pprint
# import pymongo
# import re
# import redis
# import shutil
import subprocess
import sys
# import time
# import unittest

# RAPD imports
# import commandline_utils
# import detectors.detector_utils as detector_utils
# import utils
from utils.r_numbers import try_int, try_float


def run(data_file):
    """
    Run phenix.reflection_statistics and capture the output
    """
    cmd = ["phenix.reflection_statistics %s" % data_file]
    # print cmd
    p = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    # print stdout
    # print stderr
    return stdout

def parse_raw_output(raw_output, logger=False):
    """
    Parse phenix.reflection_statistics output.
    """
    if logger:
        logger.debug("parse_raw_output")

    # Handle raw output types
    if isinstance(raw_output, str):
        if len(raw_output) > 250:
            raw_output = raw_output.split("\n")
        else:
            if os.path.exists(raw_output):
                raw_output = open(raw_output, "r").readlines()
            else:
                print "Sorry, I think you are inputing a file name, but I cannot find the file"
                raise ValueError(
                    "Sorry, I think you are inputing a file name, but I cannot find the file")

    output_lines = []
    anom_lines = []
    anom = {}
    anomalous_present = True
    pat = {}
    twin_info = {}
    patterson_positive = False
    patterson_p_value = 0
    twin = False
    final_verdict_line = False
    # Index for list of Patterson peaks
    pat_st = 0
    pat_dist = 0.0
    skip = True
    pat_info = {}
    coset = []
    verdict_text = []

    # Can be multiple summaries
    summary_number = None
    centric_reflections = {}
    completeness = {}
    completeness_infinity = {}
    completeness_table = {}
    miller_array_labels = {}
    observation_type = {}
    patterson_peak_table = {}
    perfect_mero_twin_table = {}
    resolution_range = {}
    space_group = {}
    space_group_intensities = {}
    space_group_metric = {}
    space_group_number = {}
    systematic_absences = {}
    unit_cell = {}
    wavelength = {}

    # Flags used in parsing tables
    in_completeness_table = False
    in_patterson_peak_table = False
    in_perfect_mero_twin_table = False

    # # Tables with an embedded label
    # tables = {}
    # table_labels = (
    #     "Completeness and data strength",
    #     "Mean intensity by shell (outliers)",
    #     # "NZ test",
    #     "L test, acentric data",
    # )

    # # Tables that lack an embedded label
    # unlabeled_tables = {}
    # unlabeled_table_labels = (
    #     "Low resolution completeness analyses",
    #     "Completeness (log-binning)",
    #     "Measurability of anomalous signal",
    #     "Ice ring related problems",
    #     "Table of systematic absence rules",
    #     "Space group identification",
    # )

    # # Tables only in the loggraph sections
    # loggraph_tables = {}
    # loggraph_table_labels = (
    #     "Intensity plots",
    #     "Measurability of Anomalous signal",
    #     "NZ test",
    #     "L test, acentric data"
    # )

    # # Table coilumns that need special handling
    # table_special_columns = (
    #     "Completeness",
    #     "Res. range",
    #     "Resolution range",
    #     "Resolution",
    #     "N(obs)/N(possible)",
    #     "Reflections",
    #     "Operator",  # str
    #     "# expected systematic absences",  # int
    #     "<I/sigI> (violations)",  # complicated
    #     "# expected non absences",  # int
    #     "# other reflections",  # int
    #     "space group",
    #     "# absent",
    #     "+++",
    #     "---",
    #     "Expected rel. I",
    # )

    stop = 1000000
    for index, line in enumerate(raw_output):

        # print index, line

        if stop == index:
            break

        # Store a copy
        output_lines.append(line)

        # Summary
        if line.startswith("Summary"):
            summary_number = int(line.split()[1])

        # Miller array info for this summary
        elif line.startswith("Miller array info"):
            miller_array_labels[summary_number] = line.split(":")[2].split(",")
            print "    miller_array_labels", miller_array_labels

        # Observation type for this summary
        elif line.startswith("Observation type"):
            observation_type[summary_number] = line.split(":")[1].strip()
            print "    observation_type", observation_type

        # Unit cell for this summary
        elif line.startswith("Unit cell: ("):
            unit_cell[summary_number] = [float(i) for i in line.replace(
                "Unit cell: (", "").replace(")", "").split(",")]
            print "    unit_cell", unit_cell

        # Space group for this summary
        elif line.startswith("Space group:"):
            space_group[summary_number] = line.replace(
                "Space group: ", "").split("(")[0].strip()
            space_group_number[summary_number] = int(line.replace(
                "Space group: ", "").split("(")[1].strip()[4:-1])
            print "    space_goup", space_group
            print "    space_goup_number", space_group_number

        # Systematic absences:
        elif line.startswith("Systematic absences:"):
            systematic_absences[summary_number] = int(line.split()[2])
            print "    systematic_absences", systematic_absences

        # Centric reflections:
        elif line.startswith("Centric reflections:"):
            centric_reflections[summary_number] = int(line.split()[2])
            print "    centric_reflections", centric_reflections

        # Resolution range:
        elif line.startswith("Resolution range:"):
            resolution_range[summary_number] = [
                float(i) for i in line.replace("Resolution range:", "").split()]
            print "    resolution_range", resolution_range

        # Completeness in resolution range:
        elif line.startswith("Completeness in resolution range:"):
            completeness[summary_number] = float(line.split(":")[1])
            print "    completeness", completeness

        # Completeness with d_max=infinity:
        elif line.startswith("Completeness with d_max=infinity:"):
            completeness_infinity[summary_number] = float(line.split(":")[1])
            print "    completeness_infinity", completeness_infinity

        # Wavelength:
        elif line.startswith("Wavelength:"):
            wavelength[summary_number] = float(line.split(":")[1])
            print "    wavelength", wavelength

        # Space group of the intensities:
        elif line.startswith("Space group of the intensities:"):
            space_group_intensities[summary_number] = line.split(":")[
                1].strip()
            print "    space_group_intensities", space_group_intensities

        # Space group of the metric:
        elif line.startswith("Space group of the metric:"):
            space_group_metric[summary_number] = line.split(":")[1].strip()
            print "    space_group_metric", space_group_metric

        # Completeness table
        elif line.startswith("Completeness of "):
            in_completeness_table = True
            first_unused = False
            completeness_table = {summary_number: {"label": [], "lo_res": [
            ], "hi_res": [],  "observed": [], "possible": [], "fraction": []}}

        # Patterson peaks for
        elif line.startswith("Patterson peaks for "):
            in_patterson_peak_table = True
            patterson_peak_table = {summary_number: []}

        # Perfect merohedral twinning test for
        elif line.startswith("Perfect merohedral twinning test for "):
            in_perfect_mero_twin_table = True
            first_unused = False
            perfect_mero_twin_table = {summary_number: {"label": [], "lo_res": [], "hi_res": [
            ],  "observed": [], "possible": [], "<I^2>/(<I>)^2": [], "(<F>)^2/<F^2>": []}}

        # Parsing Patterson peak table
        if in_patterson_peak_table:
            sline = line.split()
            if len(sline) == 5:
                peak = {
                    "x": float(sline[0]),
                    "y": float(sline[1]),
                    "z": float(sline[2]),
                    "height": float(sline[3]),
                    "distance": float(sline[4])
                }
                patterson_peak_table[summary_number].append(peak)

            # Table done
            if not line.strip():
                in_patterson_peak_table = False
                pprint(patterson_peak_table)

        # Parsing a perfect merohedral twinning table
        if in_perfect_mero_twin_table:
            record = False
            sline = line.split()

            # Unused reflection range
            if line.startswith("unused"):
                record = True
                label = "unused"

                # Variance between low res unused an hi res
                # Low res
                if not first_unused:
                    first_unused = True
                    lo_res = None
                    hi_res = float(sline[2])
                    observed = int(sline[4].split("/")[0])
                    possible = int(sline[4].split("/")[1])
                    i_stat = None
                    f_stat = None
                # Hi res
                else:
                    first_unused = False
                    lo_res = float(sline[1])
                    hi_res = None
                    observed = int(sline[4].split("/")[0])
                    possible = int(sline[4].split("/")[1])
                    fraction = None
                    i_stat = None
                    f_stat = None

            # Regular bin lines
            # bin 24:  1.2838 -  1.2658 [2465/2603]  2.2938  0.7327
            elif line.startswith("bin "):
                record = True
                label = ("bin "+sline[1]).replace(":", "")
                lo_res = float(sline[2])
                hi_res = float(sline[4])
                observed = int(sline[5].replace(
                    "[", "").replace("]", "").split("/")[0])
                possible = int(sline[5].replace(
                    "[", "").replace("]", "").split("/")[1])
                i_stat = float(sline[6])
                f_stat = float(sline[7])

            # The average line
            elif line.strip().startswith("average: "):
                print sline
                record = False
                perfect_mero_twin_table[summary_number]["average_<I^2>/(<I>)^2"] = float(
                    sline[1])
                perfect_mero_twin_table[summary_number]["average_(<F>)^2/<F^2>"] = float(
                    sline[2])

            # The table is over
            elif not line.strip():
                in_perfect_mero_twin_table = False
                stop = index + 10
                pprint(perfect_mero_twin_table)

            if record:
                perfect_mero_twin_table[summary_number]["label"].append(
                    label)
                perfect_mero_twin_table[summary_number]["lo_res"].append(
                    lo_res)
                perfect_mero_twin_table[summary_number]["hi_res"].append(
                    hi_res)
                perfect_mero_twin_table[summary_number]["observed"].append(
                    observed)
                perfect_mero_twin_table[summary_number]["possible"].append(
                    possible)
                perfect_mero_twin_table[summary_number]["<I^2>/(<I>)^2"].append(
                    i_stat)
                perfect_mero_twin_table[summary_number]["(<F>)^2/<F^2>"].append(
                    f_stat)

            # Parsing a completeness table
        if in_completeness_table:

            record = False

            # Unused reflection range
            if line.startswith("unused"):
                record = True
                label = "unused"
                sline = line.split()

                # Variance between low res unused an hi res
                # Low res
                if not first_unused:
                    first_unused = True
                    lo_res = None
                    hi_res = float(sline[2])
                    observed = int(sline[4].split("/")[0])
                    possible = int(sline[4].split("/")[1])
                    fraction = None
                # Hi res
                else:
                    first_unused = False
                    lo_res = float(sline[1])
                    hi_res = None
                    observed = int(sline[4].split("/")[0])
                    possible = int(sline[4].split("/")[1])
                    fraction = None

            # Regular bin lines
            elif line.startswith("bin "):
                record = True
                sline = line.split()
                label = ("bin "+sline[1]).replace(":", "")
                lo_res = float(sline[2])
                hi_res = float(sline[4])
                observed = int(sline[5].replace(
                    "[", "").replace("]", "").split("/")[0])
                possible = int(sline[5].replace(
                    "[", "").replace("]", "").split("/")[1])
                fraction = float(sline[6])

            # The table is over
            elif not line.strip():
                in_completeness_table = False
                pprint(completeness_table)

            if record:
                completeness_table[summary_number]["label"].append(label)
                completeness_table[summary_number]["lo_res"].append(lo_res)
                completeness_table[summary_number]["hi_res"].append(hi_res)
                completeness_table[summary_number]["observed"].append(observed)
                completeness_table[summary_number]["possible"].append(possible)
                completeness_table[summary_number]["fraction"].append(fraction)

    #     # Spacegroup information
    #     if line.startswith("Space group:"):
    #         sg_full = line.replace("Space group:", "").strip()   # strip().split(":")[1].strip()
    #         sg_text = sg_full.split("(")[0].strip()
    #         sg_num = int(sg_full.split("(")[1].split()[1].replace(")", ""))
    #         continue

    #     # Unit cell info
    #     if line.startswith("Unit cell:"):
    #         unit_cell_full = line.strip().split(":")[1].strip().replace("(", "").replace(")", "")
    #         a, b, c, alpha, beta, gamma = [float(x) for x in line.strip().split(":")[1].strip().\
    #             replace("(", "").replace(")", "").split(",")]
    #         continue

    #     # Final verdict of xtriage
    #     if "Final verdict" in line:
    #         final_verdict_line = index
    #         continue

    #     if line.startswith("bin "):
    #         anom_lines.append(line)
    #         continue

    #     if "There seems to be no real significant anomalous differences in this dataset" in line:
    #         anomalous_present = False
    #         continue

    #     # A Table is found
    #     for table_label in table_labels:
    #         if line.startswith("  | "+table_label):
    #             tables[table_label] = index
    #             continue

    #     # A table with no label is found
    #     for table_label in unlabeled_table_labels:
    #         # print table_label
    #         if "--"+table_label+"--" in line:
    #             # print ">>>>", index, line
    #             unlabeled_tables[table_label] = index
    #             continue

    #     # A loggraph table of interest is found
    #     for table_label in loggraph_table_labels:
    #         if "TABLE: "+table_label in line:
    #             # print ">>>>", index, line
    #             loggraph_tables[table_label] = index
    #             continue

    #     # Z score
    #     if line.startswith("  Multivariate Z score"):
    #         z_score = float(line.split()[4])
    #         continue

    #     # Patterson analysis
    #     if line.startswith("Patterson analyses"):
    #         index_patterson = index
    #         continue
    #     if line.startswith(" Frac. coord."):
    #         pat_x = line.split()[3]
    #         pat_y = line.split()[4]
    #         pat_z = line.split()[5]
    #         continue
    #     if line.startswith(" Distance to origin"):
    #         pat_dist = float(line.split()[4])
    #         continue
    #     if line.startswith(" Height (origin=100)"):
    #         pat_height = float(line.split()[3])/100.0
    #         continue
    #     if "Height relative to origin" in line:
    #         pat_height = float(line.split()[5])/100.0
    #         continue
    #     if "p_value(" in line:
    #         patterson_p_value = float(line.split()[2])
    #         if patterson_p_value <= 0.05:
    #             patterson_positive = True
    #         continue
    #     # There is a list of patterson peaks
    #     if line.startswith("The full list of Patterson peaks is:"):
    #         pat_st = index
    #         continue

    #     # Systematic absences
    #     if line.startswith("Systematic absences"):
    #         pat_fn = index
    #         continue

    #     # Twinning
    #     if line.startswith("| Type | Axis   | R metric"):
    #         twin = True
    #         twin_st = index
    #         continue
    #     if line.startswith("M:  Merohedral twin law"):
    #         twin_fn = index
    #         continue
    #     if line.startswith("Statistics depending on twin"):
    #         twin2_st = index
    #         continue
    #     if line.startswith("  Coset number"):
    #         coset.append(index)
    #         continue

    # if pat_dist:
    #     data2 = {"frac x": float(pat_x),
    #              "frac y": float(pat_y),
    #              "frac z": float(pat_z),
    #              "peak": pat_height,
    #              "p-val": patterson_p_value,
    #              "dist": pat_dist
    #             }
    #     pat["1"] = data2

    # else:
    #     skip = False

    # # Handle the final verdict lines
    # if final_verdict_line:
    #     for line in output_lines[final_verdict_line+1:]:
    #         if "------" in line:
    #             break
    #         elif line.strip():
    #             verdict_text.append(line.strip())
    # else:
    #     verdict_text.append("No verdict")

    # # Handle list of Patterson peaks
    # if pat_st:
    #     i = 2
    #     for line in output_lines[pat_st+2:pat_fn]:
    #         split = line.split()
    #         if line.startswith("("):
    #             if not skip:
    #                 x_frac = float(line[1:7].replace(" ", ""))
    #                 y_frac = float(line[8:14].replace(" ", ""))
    #                 z_frac = float(line[15:21].replace(" ", ""))
    #                 pk_height = float(line[25:34].replace(" ", ""))
    #                 p_value = float(line[38:-2].replace(" ", ""))
    #                 data = {"frac x": x_frac,
    #                         "frac y": y_frac,
    #                         "frac z": z_frac,
    #                         "peak": pk_height,
    #                         "p-val": p_value,
    #                        }
    #                 pat[str(i)] = data
    #                 i += 1
    #             skip = False
    #         if line.startswith(" space group"):
    #             patterson_positive = True
    #             pts_sg = output_lines.index(line)
    #             i1 = 1
    #             for line2 in output_lines[pts_sg+1:pat_fn]:
    #                 if line2.split() != []:
    #                     a = line2.find("(")
    #                     b = line2.find(")")
    #                     c = line2.rfind("(")
    #                     d = line2.rfind(")")
    #                     sg = line2[:a-1].replace(" ", "")+" "+line2[a:b+1].replace(" ", "")
    #                     op = line2[b+1:c].replace(" ", "")
    #                     ce = line2[c+1:d]
    #                     data2 = {"space group": sg,
    #                              "operator": op,
    #                              "cell": ce}
    #                     pat_info[i1] = data2
    #                     i1 += 1

    # # Handle twinning
    # if twin:
    #     for line in output_lines[twin_st+2:twin_fn-1]:
    #         split = line.split()
    #         law = split[11]
    #         data = {"type": split[1],
    #                 "axis": split[3],
    #                 "r_metric": split[5],
    #                 "d_lepage": split[7],
    #                 "d_leb": split[9]}
    #         twin_info[law] = data

    #     for line in output_lines[twin2_st+4:index_patterson-2]:
    #         split = line.split()
    #         law = split[1]
    #         data = {"r_obs": split[5],
    #                 "britton": split[7],
    #                 "h-test": split[9],
    #                 "ml": split[11]}
    #         twin_info[law].update(data)

    #     if len(coset) > 0:
    #         for line in coset[1:]:
    #             sg = output_lines[line][38:-2]
    #             #   try:
    #             for i in range(2, 4):
    #                 if len(output_lines[line+i].split()) > 0:
    #                     law = output_lines[line+i].split()[1]
    #                     if twin_info.has_key(law):
    #                         twin_info[law].update({"sg":sg})
    #             #   except:
    #             #     self.logger.exception("Warning. Missing Coset info.")
    #     else:
    #         crap = {"sg":"NA"}
    #         for key in twin_info.keys():
    #             twin_info[key].update(crap)

    # for line in anom_lines[10:20]:
    #     if len(line.split()) == 7:
    #         anom[line.split()[4]] = line.split()[6]
    #     else:
    #         anom[line.split()[4]] = "0.0000"

    # # Grab the tables
    # for table_label in table_labels:
    #     # print "Grabbing tables"
    #     # print "table_label", table_label

    #     try:
    #         table_start = tables[table_label]
    #         # print "table_start", table_start
    #     except KeyError:
    #         continue

    #     column_labels = []
    #     column_data = {}
    #     column_labels = []
    #     have_header = False
    #     have_body = False
    #     for line in output_lines[table_start:]:
    #         # print line
    #         # Skip dividers
    #         if "----" in line:
    #             if have_body:
    #                 break
    #             else:
    #                 continue
    #         elif not have_header:
    #             sline = line.split(" | ")
    #             # print sline
    #             if len(sline) > 3:
    #                 for item in sline:
    #                     label = item.strip()
    #                     if label:
    #                         column_labels.append(label)
    #                 column_labels[-1] = column_labels[-1].rstrip(" |")
    #                 for column_label in column_labels:
    #                     if column_label in table_special_columns:
    #                         if column_label == "Res. range":
    #                             column_data["Low Res"] = []
    #                             column_data["High Res"] = []
    #                     else:
    #                         column_data[column_label] = []
    #                 have_header = True
    #         else:
    #             have_body = True
    #             # print line
    #             sline = line[4:-2].split("|")
    #             # print sline
    #             for position, value in enumerate(sline):
    #                 if column_labels[position] in table_special_columns:
    #                     if column_labels[position] == "Res. range":
    #                         column_data["Low Res"].append(float(value.split("-")[0].strip()))
    #                         column_data["High Res"].append(float(value.split("-")[1].strip()))
    #                     elif column_label in ("Completeness",):
    #                         if "%" in value:
    #                             column_data[column_label].append(float(value.\
    #                                 replace("%", ""))/100.0)
    #                         else:
    #                             column_data[column_labels[position]].append(float(value.strip()))
    #                 else:
    #                     column_data[column_labels[position]].append(float(value.strip()))
    #     # pprint(column_data)
    #     tables[table_label] = column_data

    # # Grab tables missing embedded labels
    # for table_label in unlabeled_table_labels:
    #     # print "Grabbing tables"
    #     # print "table_label", table_label

    #     try:
    #         table_start = unlabeled_tables[table_label]
    #     except KeyError:
    #         continue

    #     # Already have the table?
    #     if table_label in tables:
    #         continue

    #     column_labels = []
    #     column_data = {}
    #     column_labels = []
    #     started_table = False
    #     have_header = False
    #     have_body = False
    #     for line in output_lines[table_start+1:]:
    #         # print line
    #         # Skip dividers
    #         if "----" in line:
    #             if not started_table:
    #                 started_table = True
    #                 continue
    #             if have_body:
    #                 break
    #             else:
    #                 continue
    #         elif started_table:
    #             if not have_header:
    #                 sline = line.split(" | ")
    #                 # print sline
    #                 if len(sline) > 3:
    #                     for item in sline:
    #                         label = item.strip()
    #                         if label:
    #                             column_labels.append(label)
    #                     column_labels[-1] = column_labels[-1].rstrip(" |")
    #                     for column_index, column_label in enumerate(column_labels):
    #                         if column_label in table_special_columns:
    #                             if column_label in ("Res. range", "Resolution range", "Resolution"):
    #                                 column_data["Low Res"] = []
    #                                 column_data["High Res"] = []
    #                             elif column_label == "<I/sigI> (violations)":
    #                                 if column_index == 2:
    #                                     column_data["Expected absences <I/sigI>"] = []
    #                                     column_data["Expected absences #"] = []
    #                                     column_data["Expected absences %"] = []
    #                                 elif column_index == 4:
    #                                     column_data["Expected non absences <I/sigI>"] = []
    #                                     column_data["Expected non absences #"] = []
    #                                     column_data["Expected non absences %"] = []
    #                                 elif column_index == 6:
    #                                     column_data["Other reflections <I/sigI>"] = []
    #                                     column_data["Other reflections #"] = []
    #                                     column_data["Other reflections %"] = []
    #                             elif column_label == "Expected rel. I":
    #                                 column_data[column_label.replace(".", "")] = []
    #                             else:
    #                                 column_data[column_label] = []
    #                         else:
    #                             column_data[column_label] = []
    #                         have_header = True
    #             else:
    #                 have_body = True
    #                 # print line
    #                 sline = line[4:-2].split("|")
    #                 # print sline
    #                 for column_index, value in enumerate(sline):
    #                     column_label = column_labels[column_index]
    #                     # print ">>>%s<<<" % column_label
    #                     if column_label in table_special_columns:
    #                         if column_label in ("Res. range", "Resolution range", "Resolution"):
    #                             column_data["Low Res"].append(float(value.split("-")[0].strip()))
    #                             column_data["High Res"].append(float(value.split("-")[1].strip()))
    #                         elif column_label == "N(obs)/N(possible)":
    #                             column_data[column_label].append(value.strip().replace("[", "").\
    #                                 replace("]", ""))
    #                         elif column_label in ("Reflections",
    #                                               "space group"):
    #                             column_data[column_label].append(value.strip())
    #                         elif column_label in ("Completeness",):
    #                             if "%" in value:
    #                                 column_data[column_label].append(float(value.replace("%",
    #                                                                                      ""))/100.0)
    #                             else:
    #                                 column_data[column_label].append(float(value.strip()))

    #                         elif column_label == "<I/sigI> (violations)":
    #                             isigi, number, percentage = value.replace("(", "").\
    #                                 replace(")", "").replace(",", "").split()
    #                             if column_index == 2:
    #                                 column_data["Expected absences <I/sigI>"].append(float(isigi))
    #                                 column_data["Expected absences #"].append(int(number))
    #                                 column_data["Expected absences %"].append(float(percentage.\
    #                                     replace("%", ""))/100.0)
    #                             if column_index == 4:
    #                                 column_data["Expected non absences <I/sigI>"].\
    #                                     append(float(isigi))
    #                                 column_data["Expected non absences #"].append(int(number))
    #                                 column_data["Expected non absences %"].append(float(percentage.\
    #                                     replace("%", ""))/100.0)
    #                             if column_index == 6:
    #                                 column_data["Other reflections <I/sigI>"].append(float(isigi))
    #                                 column_data["Other reflections #"].append(int(number))
    #                                 column_data["Other reflections %"].append(float(percentage.\
    #                                     replace("%", ""))/100.0)
    #                         elif column_label == "Expected rel. I":
    #                             column_data[column_label.replace(".", "")].append(try_float(value.strip()))

    #                         # Integer
    #                         elif column_label in ("# absent",
    #                                               "+++",
    #                                               "---",
    #                                               "# other reflections",
    #                                               "# expected systematic absences",
    #                                               "# expected non absences"):
    #                             column_data[column_label].append(int(value.strip()))

    #                         # String
    #                         elif column_label in ("Operator", ):
    #                             column_data[column_label].append(value.strip())
    #                     else:
    #                         column_data[column_label].append(try_float(value.strip()))
    #     # pprint(column_data)
    #     tables[table_label] = column_data

    # # Loggraph tables
    # loggraph_label_mods = {
    #     "Acentric_observed": "Acentric observed",
    #     "Acentric_untwinned":"Acentric untwinned",
    #     "Centric_observed":  "Centric observed",
    #     "Centric_untwinned": "Centric untwinned",
    # }

    # for table_label in loggraph_table_labels:
    #     # print "\n\nGrabbing tables"
    #     # print "table_label", table_label

    #     try:
    #         table_start = loggraph_tables[table_label]
    #     except KeyError:
    #         continue

    #     # Already have the table?
    #     if table_label in tables:
    #         # print tables[table_label]
    #         continue

    #     column_labels = []
    #     column_data = {}
    #     column_labels = []
    #     have_header = False
    #     have_body = False
    #     for line in output_lines[table_start:]:
    #         # print line
    #         # Ignore some lines
    #         if line.startswith("$") or line.startswith(":"):
    #             if have_body:
    #                 break
    #             else:
    #                 continue

    #         elif not have_header:
    #             sline = line.split()
    #             # print sline
    #             if len(sline) > 3:
    #                 for label in sline[:-1]:
    #                     # Modify a label
    #                     if label in loggraph_label_mods:
    #                         label = loggraph_label_mods[label]
    #                     column_labels.append(label)
    #                 for column_label in column_labels:
    #                     column_data[column_label] = []
    #                     if column_label == "1/resol**2":
    #                         column_data["resol"] = []
    #                 have_header = True
    #         elif have_header:
    #             have_body = True
    #             sline = line.split()
    #             # print sline
    #             for position, value in enumerate(sline):
    #                 column_label = column_labels[position]
    #                 column_data[column_label].append(float(value))
    #                 # Store resolution for convenience sake
    #                 if column_label == "1/resol**2":
    #                     column_data["resol"].append(math.sqrt(1.0/float(value)))

    #     # if table_label == "NZ test":
    #     #     pprint(column_data)
    #     tables[table_label] = column_data

    # # Turn tables into plots
    # plots = {}

    # # Run through all the tables
    # labels_to_plot = (
    #     "Intensity plots",
    #     "Measurability of Anomalous signal",
    #     "NZ test",
    #     "L test, acentric data",
    # )
    # for table_label in labels_to_plot: # table_labels \
    #                                    # + unlabeled_table_labels \
    #                                    # + loggraph_table_labels:

    #     # print table_label

    #     top_labels = {
    #         "Intensity plots": "Intensities",
    #         "Measurability of Anomalous signal": "Anomalous Measurability",
    #         "NZ test": "NZ Test",
    #         "L test, acentric data": "L Test",
    #     }

    #     y_labels = {
    #         "Intensity plots": "",
    #         "Measurability of Anomalous signal": "",
    #         "NZ test": "",
    #         "L test, acentric data": "",
    #     }

    #     x_labels = {
    #         "Intensity plots": "Resolution (A)",
    #         "Measurability of Anomalous signal": "Resolution (A)",
    #         "NZ test": "Z",
    #         "L test, acentric data": "|L|",
    #     }

    #     # Labels to make things better
    #     override_labels = {
    #         "<I>_smooth_approximation": "<I> Smoothed",
    #     }

    #     x_columns = {
    #         "Intensity plots": "resol",
    #         "Measurability of Anomalous signal": "resol",
    #         "NZ test": "z",
    #         "L test, acentric data": "|l|",
    #     }

    #     columns_to_plot = {
    #         "Intensity plots": ("<I>_smooth_approximation",
    #                             "<I>_expected",
    #                             "<I>_via_binning",),
    #         "Measurability of Anomalous signal": ("Smooth_approximation",
    #                                               "Measurability",),
    #         "NZ test": ("Centric observed",
    #                     "Acentric observed",
    #                     "Acentric untwinned",
    #                     "Centric untwinned"),
    #         "L test, acentric data": ("Observed",
    #                                   "Acentric theory",
    #                                   "Acentric theory, perfect twin"),
    #     }

    #     if table_label in labels_to_plot:
    #         # print "  Modding plot %s" % table_label

    #         if table_label in tables:

    #             if tables[table_label]:

    #                 table_data = tables[table_label]
    #                 x_column = x_columns[table_label]
    #                 my_columns_to_plot = columns_to_plot[table_label]

    #                 plots[table_label] = {
    #                     "x_data": [],
    #                     "y_data": [],
    #                     "data": [],
    #                     "parameters": {
    #                         "toplabel": top_labels[table_label],
    #                         "x_label": x_labels[table_label],
    #                         "xlabel": x_labels[table_label],
    #                         "ylabel": y_labels[table_label]
    #                     }
    #                 }

    #                 for column_label in table_data:
    #                     # print "    %s" % column_label
    #                     if column_label in my_columns_to_plot:
    #                         plots[table_label]["data"].append({
    #                             "parameters": {
    #                                 "linelabel": column_label
    #                             },
    #                             "series": [{
    #                                 "xs": table_data[x_column],
    #                                 "ys": table_data[column_label]
    #                             }]
    #                         })
    #                         # if column_label in override_labels:
    #                         #     column_label = override_labels[column_label]

    #                         plots[table_label]["y_data"].append({
    #                             "data": table_data[column_label],
    #                             "label": column_label,
    #                             "pointRadius": 0
    #                         })
    #                     elif column_label == x_column:
    #                         plots[table_label]["x_data"] = table_data[x_column]
    #                     else:
    #                         pass
    #                     # print "    %s NOT GATHERED" % column_label

    #             # No plot for this label
    #             else:
    #                 pass

    #         # No plot for this label
    #         else:
    #             pass

    # # pprint(plots["NZ test"])

    # Assemble for return
    results = {
        "completeness": completeness,
        "completeness_infinity": completeness_infinity,
        "completeness_table": completeness_table,
        "miller_array_labels": miller_array_labels,
        "observation_type": observation_type,
        "patterson_peak_table": patterson_peak_table,
        "perfect_mero_twin_table": perfect_mero_twin_table,
        "resolution_range": resolution_range,
        "space_group": space_group,
        "space_group_intensities": space_group_intensities,
        "space_group_metric": space_group_metric,
        "space_group_number": space_group_number,
        "systematic_absences": systematic_absences,
        "unit_cell": unit_cell,
        "wavelength": wavelength
    }
    #     "anom": anom,
    #     "anomalous_present": anomalous_present,
    #     "Patterson peaks": pat,
    #     "Patterson p-value": patterson_p_value,
    #     # "summary": summary,
    #     "patterson search positive": patterson_positive,
    #     "plots": plots,
    #     "PTS info": pat_info,
    #     "spacegroup": {
    #         "number": sg_num,
    #         "text": sg_text,
    #     },
    #     "tables": tables,
    #     "twin": twin,
    #     "twin info": twin_info,
    #     "unit_cell": {
    #         "a": a,
    #         "b": b,
    #         "c": c,
    #         "alpha": alpha,
    #         "beta": beta,
    #         "gamma": gamma
    #     },
    #     "verdict_text": verdict_text,
    #     "z-score": z_score,
    # }

    pprint(results)

    if logger:
        logger.debug("parse_raw_output Done")

    return results


if __name__ == "__main__":

    print sys.argv
    raw_output = run(data_file=sys.argv[1])
    parse_raw_output(raw_output=raw_output)
