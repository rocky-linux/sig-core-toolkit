#!/bin/bash
r_log "tftp" "Testing anon write"
TFTPDIR=/var/lib/tftpboot
setsebool tftp_anon_write 1
chmod 777 $TFTPDIR
echo "rocky func" > puttest
touch $TFTPDIR > $TFTPDIR/puttest
chmod 666 $TFTPDIR/puttest
tftp 127.0.0.1 -c put puttest
sleep 2
grep -q 'rocky func' $TFTPDIR/puttest
r_checkExitStatus $?
/bin/rm puttest
/bin/rm $TFTPDIR/puttest
