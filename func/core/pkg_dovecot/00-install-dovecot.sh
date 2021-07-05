#!/bin/bash
r_log "dovecot" "Installing dovecot"
p_installPackageNormal dovecot nc grep
m_serviceCycler dovecot start
