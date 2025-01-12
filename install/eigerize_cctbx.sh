#!/bin/bash

# Modify CCTBX to handle Eiger CBF files

# if [ "$RAPD_HOME" != "" ]; then

  printf "\nRAPD_HOME set to $RAPD_HOME\n"
  for word in $@; do echo "$word"; done
  echo $@
  # SAFE_PREFIX=$(echo "$RAPD_HOME" | sed -e 's/\//\\\//g')
  #
  # # Control
  # echo "#! /bin/bash" > $RAPD_HOME/bin/rapd.control
  # echo "$SAFE_PREFIX\/bin\/rapd.python $SAFE_PREFIX\/src\/utils\/overwatch.py --managed_file $SAFE_PREFIX\/src\/control\/rapd_control.py \"\$@\"" >>$RAPD_HOME/bin/rapd.control
  # chmod +x $RAPD_HOME/bin/rapd.control
  #
  # # Print out basic detctor information
  # echo "#! /bin/bash" > $RAPD_HOME/bin/rapd.print_detector
  # echo "$SAFE_PREFIX\/bin\/rapd.python $SAFE_PREFIX\/src\/detectors\/detector_utils.py \"\$@\"" >>$RAPD_HOME/bin/rapd.print_detector
  # chmod +x $RAPD_HOME/bin/rapd.print_detector
  #
  # # Convert Eiger HDF5 files to CBFs
  # echo "#! /bin/bash" > $RAPD_HOME/bin/rapd.h5_to_cbf
  # echo "$SAFE_PREFIX\/bin\/rapd.python $SAFE_PREFIX\/src\/utils\/convert_hdf5_cbf.py \"\$@\"" >>$RAPD_HOME/bin/rapd.h5_to_cbf
  # chmod +x $RAPD_HOME/bin/rapd.h5_to_cbf
  # ln -s $RAPD_HOME/bin/rapd.h5_to_cbf $RAPD_HOME/bin/rapd.hdf5_to_cbf
  # ln -s $RAPD_HOME/bin/rapd.h5_to_cbf $RAPD_HOME/bin/rapd.eiger_to_cbf
  #
  # # Index
  # echo "#! /bin/bash" > $RAPD_HOME/bin/rapd.index
  # echo "$SAFE_PREFIX\/bin\/rapd.python $SAFE_PREFIX\/src\/commandline\/index+strategy.py \"\$@\"" >>$RAPD_HOME/bin/rapd.index
  # chmod +x $RAPD_HOME/bin/rapd.index
  #
  # # Integrate
  # echo "#! /bin/bash" > $RAPD_HOME/bin/rapd.integrate
  # echo "# Make sure we can run XDS" > $RAPD_HOME/bin/rapd.integrate
  # echo "unamestr=`uname`" > $RAPD_HOME/bin/rapd.integrate
  # echo "if [[ "$unamestr" == 'Darwin' ]]; then" > $RAPD_HOME/bin/rapd.integrate
  # echo "   ulimit -s 65532" > $RAPD_HOME/bin/rapd.integrate
  # echo "fi" > $RAPD_HOME/bin/rapd.integrate
  # echo "# Call rapd_integrate" > $RAPD_HOME/bin/rapd.integrate
  # echo "$SAFE_PREFIX\/bin\/rapd.python $SAFE_PREFIX\/src\/commandline\/rapd_integrate.py \"\$@\"" >>$RAPD_HOME/bin/rapd.integrate
  # chmod +x $RAPD_HOME/bin/rapd.integrate

# Environmental var not set - don't run
# else
#   echo "The RAPD_HOME environmental variable must be set. Exiting"
#   exit
# fi
