#!/bin/bash
r_log "sysstat" "Testing CPU load is being measured via mpstat"

TMPFILE=/var/tmp/mpstat
BLOCKS=4096
COUNT=20000

[ -e "$TMPFILE" ] && /bin/rm -f $TMPFILE

/usr/bin/mpstat -P 0 1 5 > $TMPFILE &

# wait
sleep 5

# generate cpu stuff
/bin/dd if=/dev/urandom bs=$BLOCKS count=$COUNT 2> /dev/null | sha256sum -b - &> /dev/null

# wait
sleep 5

# Check that our bytes are greater than zero. Except the first line.
CPU_SYS_PERCENT=$(awk '$6 ~ /[0-9]\./ {$6>a ? a=$6 : $6} END {print int(a)}' $TMPFILE)

[ "$CPU_SYS_PERCENT" -gt 5 ] || { r_log "sysstat" "Why didn't we log CPU activity..."; }

r_checkExitStatus $?
