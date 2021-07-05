#!/bin/bash
r_log "vsftpd" "Test local logins"

getent passwd ftprocky | grep -q "ftprocky"
ret_val=$?

if [ $ret_val -ne 0 ]; then
  useradd ftprocky
fi

echo ftptest | passwd --stdin ftprocky
setsebool ftp_home_dir 1

echo -e 'user ftprocky\npass ftptest\nquit' | nc localhost 21 | grep -q '230 Login successful.'

r_checkExitStatus $?

userdel -rf ftprocky
