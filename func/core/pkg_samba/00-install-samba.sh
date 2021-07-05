#!/bin/bash
r_log "samba" "Install samba"
p_installPackageNormal samba samba-client cifs-utils
m_serviceCycler smb start
