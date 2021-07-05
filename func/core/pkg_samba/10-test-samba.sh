#!/bin/bash
r_log "sambsa" "Configure and test samba for a simple share"
/bin/cp /etc/samba/smb.conf /etc/samba/smb.conf.backup
/bin/cp ./common/files/smb.conf /etc/samba/smb.conf
mkdir -p /srv/smb
mkdir -p /mnt/smb
chcon -R -t samba_share_t /srv/smb

m_serviceCycler smb restart
sleep 3

echo "Obsidian is the Release Name" > /srv/smb/test.txt

mount -t cifs -o guest,ro //127.0.0.1/rocky /mnt/smb
sleep 1

cat /mnt/smb/test.txt | grep -q "Obsidian"

ret_val=$?
umount /mnt/smb
/bin/rm -rf /mnt/smb

r_checkExitStatus $ret_val
