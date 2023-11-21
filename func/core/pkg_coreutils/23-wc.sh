#!/bin/bash
r_log "coreutils" "Ensure wc works as expected"
r_log "coreutils" "This should have already been done with uniq"
# Context: we should probably test some switches...
trap "/bin/rm /var/tmp/wc" EXIT

cat > /var/tmp/wc <<EOF
Rocky
Rocky
Obsidian
obsidian
Green
Green
Blue
onynx
EOF

wc -l /var/tmp/wc | grep -q 8 && \
wc -c /var/tmp/wc | grep -q 53 && \
wc -m /var/tmp/wc | grep -q 53 && \
wc -L /var/tmp/wc | grep -q 8 && \
wc -w /var/tmp/wc | grep -q 8

r_checkExitStatus $?
