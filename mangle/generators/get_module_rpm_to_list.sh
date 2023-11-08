#!/bin/bash
for x in $(cat list); do
  NAME=$(echo $x | cut -d ':' -f 1)
  STREAM=$(echo $x | cut -d ':' -f 2)
  git clone ssh://git.rockylinux.org:22220/staging/modules/${NAME} -b r8s-stream-${STREAM}
  if [ $? -eq 0 ]; then
    pushd $NAME
    cat ${NAME}.yaml | yq '.data.components.rpms  | keys[]' | sed 's/"//g' > ../${NAME}:${STREAM}.list
    popd
    rm -rf ${NAME}
    fi
done
