#!/bin/bash
r_log "archive" "Testing zforce"

BASEFILE="/var/tmp/abcdefg"
/bin/rm $BASEFILE* &>/dev/null

cat > $BASEFILE <<EOF
Green Obsidian is our release name
EOF

gzip $BASEFILE
mv $BASEFILE.gz $BASEFILE

zforce $BASEFILE || r_checkExitStatus 1
[ -e "$BASEFILE.gz" ]
r_checkExitStatus $?

/bin/rm "$BASEFILE.gz"
