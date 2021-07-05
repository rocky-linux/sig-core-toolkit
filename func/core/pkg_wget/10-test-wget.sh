#!/bin/bash
r_log "wget" "Test wget works as intended"

URL=http://dl.rockylinux.org
FILE=/var/tmp/dlrocky.html
CHECK="pub/"

r_log "wget" "Querying: ${URL}"
wget -q -O ${FILE} ${URL}
grep -q "${CHECK}" "${FILE}"

r_checkExitStatus $?
/bin/rm ${FILE}
