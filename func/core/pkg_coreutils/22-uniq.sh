#!/bin/bash
r_log "coreutils" "Ensure uniq works as expected"
trap '/bin/rm /var/tmp/uniq' EXIT

cat > /var/tmp/uniq <<EOF
Rocky
Rocky
Obsidian
obsidian
Green
Green
Blue
onyn
EOF

uniq -d /var/tmp/uniq | wc -l | grep -q 2 && uniq -u /var/tmp/uniq | wc -l | grep -q 4
r_checkExitStatus $?
