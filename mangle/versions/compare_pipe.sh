#!/bin/bash
if [ -f /tmp/old_newer ]; then
  /bin/rm /tmp/old_newer
fi
if [ -f /tmp/new_newer ]; then
  /bin/rm /tmp/new_newer
fi
for x in $(cat /tmp/endgame); do
  VER1_NAME=$(echo ${x} | cut -d'|' -f 1 | sed 's/^\(.*\)-\([^-]\{1,\}\)-\([^-]\{1,\}\)$/\1/')
  VER1_EPO=$(echo ${x} | cut -d'|' -f 1 | sed 's/^\(.*\)-\([^-]\{1,\}\)-\([^-]\{1,\}\)$/\2/' | cut -d':' -f1)
  VER1_VER=$(echo ${x} | cut -d'|' -f 1 | sed 's/^\(.*\)-\([^-]\{1,\}\)-\([^-]\{1,\}\)$/\2/')
  VER1_REL=$(echo ${x} | cut -d'|' -f 1 | sed 's/^\(.*\)-\([^-]\{1,\}\)-\([^-]\{1,\}\)$/\3/')
  VER2_NAME=$(echo ${x} | cut -d'|' -f 2 | sed 's/^\(.*\)-\([^-]\{1,\}\)-\([^-]\{1,\}\)$/\1/')
  VER2_EPO=$(echo ${x} | cut -d'|' -f 2 | sed 's/^\(.*\)-\([^-]\{1,\}\)-\([^-]\{1,\}\)$/\2/' | cut -d':' -f1)
  VER2_VER=$(echo ${x} | cut -d'|' -f 2 | sed 's/^\(.*\)-\([^-]\{1,\}\)-\([^-]\{1,\}\)$/\2/')
  VER2_REL=$(echo ${x} | cut -d'|' -f 2 | sed 's/^\(.*\)-\([^-]\{1,\}\)-\([^-]\{1,\}\)$/\3/')
  VER1=$(echo ${x} | cut -d'|' -f 1)
  VER2=$(echo ${x} | cut -d'|' -f 2)
  rpmdev-vercmp ${VER1_EPO} ${VER1_VER} ${VER1_REL} ${VER2_EPO} ${VER2_VER} ${VER2_REL} 2>&1 > /dev/null
  ret_val=$?
  if [[ "$ret_val" -eq "11" ]]; then
    echo ${VER1} >> /tmp/old_newer
  fi
  if [[ "$ret_val" -eq "12" ]]; then
    echo ${VER2} >> /tmp/new_newer
  fi
done

echo "Files generated: /tmp/old_newer /tmp/new_newer"
