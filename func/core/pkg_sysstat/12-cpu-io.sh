#!/bin/bash
r_log "sysstat" "Test CPU measurements via iostat"

TMPFILE=/var/tmp/iostat.cpi
DISK=$(fdisk -l|grep -Po -m1 '^/dev/[\D]+')
BLOCKS=4096
COUNT=20000


# drop caches
echo 1 > /proc/sys/vm/drop_caches

[ -e "$TMPFILE" ] && /bin/rm -f $TMPFILE

/usr/bin/iostat -c 1 5 > $TMPFILE &

# wait
sleep 5

/bin/dd if="$DISK" bs=$BLOCKS count=$COUNT 2> /dev/null | sha256sum -b - &> /dev/null

# wait
sleep 5

CPU_USER_PERCENT=$(awk '$1 ~ /[0-9]/ {$1>a ? a=$1 : $1} END {print int(a)}' $TMPFILE)

[ "$CPU_USER_PERCENT" -gt 3 ] || { r_log "sysstat" "Why aren't we generating activity..."; }

r_checkExitStatus $?
