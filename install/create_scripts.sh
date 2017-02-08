#!/bin/bash

# Create scripts used by RAPD
# These are in addition to those created by the creat_min_scripts

if [ "$RAPD_HOME" != "" ]; then

  SAFE_PREFIX=$(echo "$RAPD_HOME" | sed -e 's/\//\\\//g')

  # Control
  echo "#! /bin/bash" > $RAPD_HOME/bin/rapd.control
  echo "$SAFE_PREFIX\/bin\/rapd.python $SAFE_PREFIX\/src\/utils\/overwatch.py --managed_file $SAFE_PREFIX\/src\/control\/rapd_control.py \"\$@\"" >>$RAPD_HOME/bin/rapd.control
  chmod +x $RAPD_HOME/bin/rapd.control

  # Index
  echo "#! /bin/bash" > $RAPD_HOME/bin/rapd.index
  echo "$SAFE_PREFIX\/bin\/rapd.python $SAFE_PREFIX\/src\/commandline\/rapd_index+strategy.py \"\$@\"" >>$RAPD_HOME/bin/rapd.index
  chmod +x $RAPD_HOME/bin/rapd.index

  # Integrate
  echo "#! /bin/bash" > $RAPD_HOME/bin/rapd.integrate
  echo "# Make sure we can run XDS" > $RAPD_HOME/bin/rapd.integrate
  echo "unamestr=`uname`" > $RAPD_HOME/bin/rapd.integrate
  echo "if [[ "$unamestr" == 'Darwin' ]]; then" > $RAPD_HOME/bin/rapd.integrate
  echo "   ulimit -s 65532" > $RAPD_HOME/bin/rapd.integrate
  echo "fi" > $RAPD_HOME/bin/rapd.integrate
  echo "# Call rapd_integrate" > $RAPD_HOME/bin/rapd.integrate
  echo "$SAFE_PREFIX\/bin\/rapd.python $SAFE_PREFIX\/src\/commandline\/rapd_integrate.py \"\$@\"" >>$RAPD_HOME/bin/rapd.integrate
  chmod +x $RAPD_HOME/bin/rapd.integrate

# Environmental var not set - don't run
else
  echo "The RAPD_HOME environmental variable must be set. Exiting"
  exit
fi
