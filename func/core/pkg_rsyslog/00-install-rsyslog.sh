#!/bin/bash
r_log "rsyslog" "Install rsyslog (default)"
p_installPackageNormal rsyslog

r_log "rsyslog" "Ensure rsyslog is started"
m_serviceCycler rsyslog start
