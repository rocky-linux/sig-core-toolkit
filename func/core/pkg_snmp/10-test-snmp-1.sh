#!/bin/bash
r_log "snmp" "Run snmpv1 test"

snmpwalk -v 1 -c public 127.0.0.1 > /dev/null 2>&1
r_checkExitStatus $?
