#!/bin/bash
r_log "sysstat" "Test basic iostat disk measurements"

TMPFILE=/var/tmp/iostat.disk
BLOCKS=4096
COUNT=10100
SUM="$(( BLOCKS * COUNT / 1024 ))"
DISK="$(fdisk -l | grep -Po -m1 '^/dev/[\D]+')"

[ -e $TMPFILE ] && /bin/rm -f $TMPFILE

# Clear out page cache
echo 1 > /proc/sys/vm/drop_caches

r_log "sysstat" "Running iostat on $DISK"
/usr/bin/iostat -dkx 1 5 "$DISK" > $TMPFILE &

# wait
sleep 4

# Generate traffic
/bin/dd if="$DISK" of=/dev/null bs=$BLOCKS count=$COUNT &> /dev/null

# wait
sleep 6

READBYTES=$(awk '$6 ~ /[0-9]/ {NR>1 && sum+=$6} END {print int(sum)}' $TMPFILE)

[ "$READBYTES" -ge "$SUM" ] || { r_log "sysstat" "It doesn't look like we got a lot of traffic. Why?"; }

r_checkExitStatus $?
