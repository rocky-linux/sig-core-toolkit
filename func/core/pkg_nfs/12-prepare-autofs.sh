#!/bin/bash
# autofs acts like it mounts but then it doesn't. this is disabled.

r_log "nfs" "Prepare autofs configuration"

mkdir -p /export/autotest
touch /export/autotest/autofile
echo '/export/autotest/ 127.0.0.1(ro)' >> /etc/exports
/usr/sbin/exportfs -ar

echo '/mnt/autofs /etc/auto.export' > /etc/auto.master.d/export.autofs
echo 'nfs -fstype=nfs 127.0.0.1:/export/autotest' > /etc/auto.export

m_serviceCycler nfs-server restart
m_serviceCycler rpcbind restart
m_serviceCycler autofs restart
r_log "nfs" "Attempt to access /export/autotest via autofs"
find /mnt/autofs | grep -q autofile
r_checkExitStatus $?

# Remove unneeded configuration
/bin/rm /etc/auto.master.d/export.autofs /etc/auto.export
/usr/bin/sed -i '/autotest/d' /etc/exports
m_serviceCycler autofs stop
m_serviceCycler nfs-server stop
m_serviceCycler rpcbind stop
