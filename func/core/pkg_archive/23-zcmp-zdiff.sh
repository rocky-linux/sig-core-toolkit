#!/bin/bash
r_log "archive" "Check zcmp and zdiff"
BASEFILE="/var/tmp/gziptest"
trap '/bin/rm -f ${BASEFILE}*' EXIT
/bin/rm -f ${BASEFILE}

cat > ${BASEFILE}.1 <<EOF
Green Obsidian is the release name
EOF

/bin/gzip ${BASEFILE}.1 || r_checkExitStatus 1
cp ${BASEFILE}.1.gz ${BASEFILE}.2.gz

r_log "archive" "Check zcmp"
/bin/zcmp ${BASEFILE}.1.gz ${BASEFILE}.2.gz || r_checkExitStatus 1

r_log "archive" "Check zdiff"
/bin/zdiff ${BASEFILE}.1.gz ${BASEFILE}.2.gz || r_checkExitStatus 1
