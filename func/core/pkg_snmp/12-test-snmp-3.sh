#!/bin/bash
r_log "snmp" "Test snmpv3"

cp /etc/snmp/snmpd.conf /etc/snmp/snmpd.conf.backup

r_log "snmp" "Create rockyro user"
cat >> /etc/snmp/snmpd.conf <<EOF
rouser rockyro
createUser rockyro MD5 rockyro DES rockyro
EOF

r_log "snmp" "Restart snmpd"
m_serviceCycler snmpd restart

r_log "snmp" "Test basic snmpv3: uptime"
snmpget -v 3 -u rockyro -n "" -l authPriv -a MD5 -A rockyro -x DES -X rockyro 127.0.0.1 sysUpTime.0 > /dev/null 2>&1
r_checkExitStatus $?

cp /etc/snmp/snmpd.conf.backup /etc/snmp/snmpd.conf
m_serviceCycler snmpd restart
