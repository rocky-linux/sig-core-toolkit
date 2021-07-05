#!/bin/bash
r_log "cron" "Installing crond"
p_installPackageNormal cronie
m_serviceCycler crond cycle
