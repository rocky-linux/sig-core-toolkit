#!/bin/bash
r_log "postfix" "Test basic MTA"
REGEX='250\ 2\.0\.0\ Ok\:\ queued\ as\ ([0-9A-Z]*).*'
mailresp=$(echo -e "helo localhost\nmail from: root@localhost\nrcpt to: root@localhost\ndata\nt_functional test\n.\nquit\n" | nc -w 5 127.0.0.1 25 | grep queued)
ret_val=$?
if [ "$ret_val" -eq 0 ]; then
  r_log "postfix" "Mail queued successfully"
  MTA_ACCEPTED=0
else
  r_log "postfix" "Mail not delivered."
  r_checkExitStatus 1
fi

sleep 2

# Verify that /var/log/maillog is working, if not dump it out
mailresp_id=$(echo "$mailresp" | cut -d' ' -f6)
grep -q "${mailresp_id}" /var/log/maillog
if [ $? -eq 1 ]; then
  journalctl -u postfix >> /var/log/maillog
fi

if [[ "$mailresp" =~ $REGEX ]]; then
  grep -q "${BASH_REMATCH[1]}: removed" /var/log/maillog
  DELIVER=$?
fi

if [ "$MTA_ACCEPTED" -eq 0 ] && [ "$DELIVER" -eq 0 ]; then
  r_log "postfix" "Mail was delivered."
  r_checkExitStatus 0
else
  r_log "postfix" "Mail was not delivered."
  r_checkExitStatus 1
fi
