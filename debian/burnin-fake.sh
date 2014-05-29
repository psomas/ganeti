#!/bin/bash

# Note: change the valuues to some that are valid for your environment

/usr/lib/ganeti/tools/burnin -p \
  -o busybox \
  -t drbd \
  --disk-size=128m --disk-growth=0 \
  --no-migrate \
  --no-replace1 --no-failover --no-import --no-add-disks --no-add-nics \
  -H fake \
  gnta-i11
