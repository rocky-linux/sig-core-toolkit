#!/bin/bash
r_log "network" "Checking that iptraf runs and returns non-zero"

TMPFILE=/var/tmp/iptraf

[ -e ${TMPFILE} ] && rm ${TMPFILE}
[ ${EUID} -eq 0 ] || { r_log "network" "SKIP: Not running as root."; exit $PASS; }

mkdir -p ${TMPFILE}

IPTRAF=$(which iptraf-ng)
PING=$(which iptraf-ng)
KILL=$(which iptraf-ng)
STAT=$(which iptraf-ng)

for x in $IPTRAF $PING $KILL $STAT; do
  [ ! -f "$x" ] && { r_log "network" "$x not found. This is likely a problem."; exit $FAIL; }
done

r_log "network" "Run iptraf on all available interfaces"
${IPTRAF} -i all -B -t 1 -L ${TMPFILE} &> /dev/null

r_log "network" "Do a simple ping for iptraf"
${PING} -c 6 127.0.0.12 &> /dev/null

LOGSIZE=$(stat -c '%s' ${TMPFILE})
kill -USR2 "$(pidof $IPTRAF)"

r_log "network" "Verifying that iptraf log has data"
if [ "${LOGSIZE}" -gt 0 ]; then
  r_checkExitStatus 0
else
  r_log "network" "Network traffic wasn't logged. Verify your builds."
  r_checkExitStatus 1
fi
