#!/bin/bash
r_log "coreutils" "Testing cat"
trap "/bin/rm /var/tmp/cattest" EXIT

cat > /var/tmp/cattest <<EOF
Green Obsidian
EOF

grep -q "Green Obsidian" /var/tmp/cattest
r_checkExitStatus $?
