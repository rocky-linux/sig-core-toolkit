#!/bin/bash
r_log "snmp" "Run snmpv2 test"

snmpwalk -v 2c -c public 127.0.0.1 > /dev/null 2>&1
r_checkExitStatus $?
