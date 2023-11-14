#!/bin/bash
r_log "archive" "Testing zforce"

BASEFILE="/var/tmp/abcdefg"
trap '/bin/rm "$BASEFILE.gz"' EXIT
/bin/rm $BASEFILE* &>/dev/null

cat > $BASEFILE <<EOF
Green Obsidian is our release name
EOF

gzip $BASEFILE
mv $BASEFILE.gz $BASEFILE

zforce $BASEFILE || r_checkExitStatus 1
[ -e "$BASEFILE.gz" ]
r_checkExitStatus $?
