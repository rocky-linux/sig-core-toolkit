#!/bin/bash
r_log "nfs" "Setup (ro) NFS share"
mkdir -p /export/rotest
touch /export/rotest/nfsfile
echo '/export/rotest/ 127.0.0.1(ro)' >> /etc/exports
/usr/sbin/exportfs -ar
m_serviceCycler rpcbind restart
m_serviceCycler nfs-server restart

r_log "nfs" "Mount NFS share"
mount -t nfs 127.0.0.1:/export/rotest /mnt
ls -la /mnt | grep -q "nfsfile"
r_checkExitStatus $?

umount /mnt
/usr/bin/sed -i '/rotest/d' /etc/exports
