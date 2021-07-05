#!/bin/bash
r_log "bind" "Installing bind"
p_installPackageNormal bind bind-utils
m_serviceCycler named start
