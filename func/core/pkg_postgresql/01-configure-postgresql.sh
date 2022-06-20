#!/bin/bash
r_log "postgresql" "Initialize postgresql"
postgresql-setup --initdb
m_serviceCycler postgresql-server cycle
sleep 15
