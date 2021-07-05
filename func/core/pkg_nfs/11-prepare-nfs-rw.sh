#!/bin/bash
r_log "nfs" "Setup (rw) NFS share"
mkdir -p /export/rwtest
touch /export/rwtest/nfsfile
echo '/export/rwtest/ 127.0.0.1(rw,sync,no_root_squash)' >> /etc/exports
/usr/sbin/exportfs -ar

m_serviceCycler rpcbind restart
m_serviceCycler nfs-server restart

r_log "nfs" "Mount NFS share"
mount -t nfs 127.0.0.1:/export/rwtest /mnt
ls -la /mnt | grep -q "nfsfile"
r_checkExitStatus $?

r_log "nfs" "Test that the NFS share is writeable"
echo 'releng test file' > /mnt/nfsfile

(grep -q 'releng test file' /mnt/nfsfile) && \
(grep -q 'releng test file' /export/rwtest/nfsfile)
ret_val=$?
r_checkExitStatus $ret_val

umount /mnt
/usr/bin/sed -i '/rwtest/d' /etc/exports
