#!/bin/bash
r_log "vsftpd" "Cleanup configs"
cp -fp /etc/vsftpd/vsftpd.conf.backup /etc/vsftpd/vsftpd.conf
m_serviceCycler vsftpd stop
