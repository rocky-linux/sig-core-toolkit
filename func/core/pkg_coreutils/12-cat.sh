#!/bin/bash
r_log "coreutils" "Testing cat"

cat > /var/tmp/cattest <<EOF
Green Obsidian
EOF

grep -q "Green Obsidian" /var/tmp/cattest
r_checkExitStatus $?

/bin/rm /var/tmp/cattest
