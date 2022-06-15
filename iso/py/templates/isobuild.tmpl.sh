#!/bin/bash
# This is a template that is used to build ISO's for Rocky Linux. Only under
# extreme circumstances should you be filling this out and running manually.

# Init the container
mock \
  -r /var/tmp/lorax-{{ major }}.cfg \
  --isolation={{ isolation }} \
  --enable-network \
  --init

cp /var/tmp/buildImage.sh \
  /var/lib/mock/{{ shortname|lower }}-{{ major }}-{{ arch }}/root/var/tmp

mock \
  -r /var/tmp/lorax-{{ major }}.cfg \
  --shell \
  --isolation={{ isolation }} \
  --enable-network -- /bin/bash /var/tmp/buildImage.sh

ret_val=$?
if [ $ret_val -eq 0 ]; then
  # Copy resulting data to /var/lib/mock/{{ shortname|lower }}-{{ major }}-{{ arch }}/result
  mkdir /var/lib/mock/{{ shortname|lower }}-{{ major }}-{{ arch }}/result
  cp /var/lib/mock/{{ shortname|lower }}-{{ major }}-{{ arch }}/root/{{ builddir }}/lorax-{{ major }}-{{ arch }}.tar.gz \
    /var/lib/mock/{{ shortname|lower }}-{{ major }}-{{ arch }}/result
else
  echo "!! LORAX RUN FAILED !!"
  exit 1
fi

# Clean up?
