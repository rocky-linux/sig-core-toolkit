#!/bin/bash
r_log "archive" "Testing zgrep"
BASEFILE=/var/tmp/zgreptest
trap '/bin/rm $BASEFILE*' EXIT
/bin/rm $BASEFILE* &> /dev/null

cat > $BASEFILE <<EOF
Green Obsidian is the release name
EOF

gzip $BASEFILE

zgrep -q 'Green Obsidian' $BASEFILE.gz
r_checkExitStatus $?
