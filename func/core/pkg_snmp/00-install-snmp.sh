#!/bin/bash
r_log "snmp" "Install net-snmp"
p_installPackageNormal net-snmp net-snmp-utils
m_serviceCycler snmpd start
