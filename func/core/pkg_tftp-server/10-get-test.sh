#!/bin/bash
r_log "tftp" "Getting a file from tftp"

chmod 777 /var/lib/tftpboot
echo "rocky func" > /var/lib/tftpboot/tftptest
tftp 127.0.0.1 -c get tftptest

grep -q "rocky func" tftptest
r_checkExitStatus $?
/bin/rm tftptest
