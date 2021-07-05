#!/bin/bash
r_log "vsftpd" "Configure vsftpd for anonymous login"

# el9 likely won't change

if [ "$RL_VER" -ge 8 ]; then
  cp -fp /etc/vsftpd/vsftpd.conf /etc/vsftpd/vsftpd.conf.backup
  sed -i 's/anonymous_enable=NO/anonymous_enable=YES/g' /etc/vsftpd/vsftpd.conf
fi

m_serviceCycler vsftpd restart

r_log "vsftpd" "Verify anonymous logins work"
echo -e 'user anonymous\npass password\nquit' | nc localhost 21 | grep -q "230 Login successful."

r_checkExitStatus $?
