#!/bin/bash

# defaults
defaultGW=$(ip route | awk '/^default via/ { print $3 }')
arpdat="/var/lib/arpwatch/arp.dat"

if [ -z "${defaultGW}" ]; then
  r_log "arpwatch" "There is no default gateway set."
  exit
fi

arpwatch
sleep 5
arp -d "${defaultGW}"
sleep 5
ping -i 1 -q -c 5 "${defaultGW}"
killall arpwatch
sleep 3
grep -q "${defaultGW}" "${arpdat}"

r_checkExitStatus $?

cat /dev/null > "${arpdat}"
