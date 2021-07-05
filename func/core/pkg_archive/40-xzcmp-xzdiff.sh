#!/bin/bash
r_log "archive" "Check xzcmp and xzdiff"
BASEFILE="/var/tmp/xztest"
/bin/rm -f ${BASEFILE}

cat > ${BASEFILE}.1 <<EOF
Green Obsidian is the release name
EOF

/bin/xz ${BASEFILE}.1 || r_checkExitStatus 1
cp ${BASEFILE}.1.xz ${BASEFILE}.2.xz

r_log "archive" "Check xzcmp"
/bin/zcmp ${BASEFILE}.1.xz ${BASEFILE}.2.xz || r_checkExitStatus 1

r_log "archive" "Check xzdiff"
/bin/zdiff ${BASEFILE}.1.xz ${BASEFILE}.2.xz || r_checkExitStatus 1

/bin/rm -f ${BASEFILE}*
