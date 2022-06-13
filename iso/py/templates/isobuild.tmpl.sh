#!/bin/bash
# This is a template that is used to build ISO's for Rocky Linux. Only under
# extreme circumstances should you be filling this out and running manually.

# Init the container
mock \
  -r /mnt/compose/9/latest-Rocky-9/work/entries/lorax-{{ major }}-{{ arch }}.cfg \
  --init

mock \
  -r /mnt/compose/9/latest-Rocky-9/work/entries/lorax-{{ major }}-{{ arch }}.cfg \
  --shell \
  --enable-network -- /bin/bash /mnt/compose/9/latest-Rocky-9/work/entries/runLorax-{{ arch }}.sh

# Clean up?
