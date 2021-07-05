#!/bin/bash
r_log "dovecot" "Testing basic IMAP"

# Note that nmap-nc appears to be the default, even in fedora
NC_OPTS="-w 5 -d 3"

r_log "dovecot" "Add imapper user and maildir"
if ! id imapper > /dev/null 2>&1; then
  useradd imapper
  echo imaptest | passwd --stdin imapper
fi

# shellcheck disable=SC2174
mkdir -m 700 -p /home/imapper/mail/.imap/INBOX
chown -R imapper:imapper /home/imapper/mail

r_log "dovecot" "Test basic IMAP login"


# shellcheck disable=SC2086
echo -e "01 LOGIN imapper imaptest\n" | nc ${NC_OPTS} localhost 143 | grep -q "Logged in."
ret_val=$?

if [ "$ret_val" -ne 0 ]; then
  tail /var/log/secure
  tail /var/log/maillog
fi

r_checkExitStatus $ret_val

userdel -rf imapper
