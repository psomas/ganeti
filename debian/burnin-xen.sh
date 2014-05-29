#!/bin/bash

# Note: change the valuues to some that are valid for your environment

/usr/lib/ganeti/tools/burnin -p \
  -o busybox \
  -t drbd \
  --disk-size=128m --disk-growth=0 \
  --reboot-types=hard,full \
  -H xen-pvm \
  gnta-i{11,12}
