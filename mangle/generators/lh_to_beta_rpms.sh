#!/bin/bash
for x in $(ls *.list) ; do
  NAME=$(echo $x | cut -d ':' -f 1)
  STREAM=$(echo ${x/.list/} | cut -d ':' -f 2)
  for rpm in $(cat ${x}); do
    git clone ssh://git.rockylinux.org:22220/staging/rpms/${rpm}.git -b r8s-stream-${STREAM}
    if [ $? -eq 0 ]; then
      pushd $rpm
      git push --delete origin $(git tag | grep r8-beta-stream-${STREAM})
      git checkout -b r8-beta-stream-${STREAM}
      #git tag -a imports/r8-beta-stream-${STREAM}/20231015200000.deadbeef -m '9.3'
      git push -f origin imports/r8-beta-stream-${STREAM}/20231015200000.deadbeef r8-beta-stream-${STREAM}
      popd
      rm -rf $rpm
    else
      echo "error"
      echo "$rpm" >> errors
      continue
    fi
  done
done
