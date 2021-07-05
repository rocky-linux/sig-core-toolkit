#!/bin/bash
r_log "dovecot" "Testing basic POP3 (does anyone still use this?)"

# Note that nmap-nc appears to be the default, even in fedora
NC_OPTS="-w 5 -d 3"

r_log "dovecot" "Add poptest user and maildir"
if ! id poptest > /dev/null 2>&1; then
  useradd poptest
  echo pop3test | passwd --stdin poptest
fi

# shellcheck disable=SC2174
mkdir -m 700 -p /home/poptest/mail/.imap/INBOX
chown -R poptest:poptest /home/poptest/mail

r_log "dovecot" "Test basic POP3 login"


# shellcheck disable=SC2086
echo -e "user poptest\npass pop3test\n" | nc ${NC_OPTS} localhost 110 | grep -q "+OK Logged in."
ret_val=$?

if [ "$ret_val" -ne 0 ]; then
  tail /var/log/secure
  tail /var/log/maillog
fi

r_checkExitStatus $ret_val

userdel -rf poptest
