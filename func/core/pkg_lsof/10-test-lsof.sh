#!/bin/bash
r_log "lsof" "Test basic lsof functions"

r_log "lsof" "lsof against sshd"
sshd_port_listen=$(lsof -i:22 | grep LISTEN)
if [ "$sshd_port_listen" ]; then
  r_log "lsof" "SSH is listening."
  ret_val=0
else
  r_log "lsof" "SSH is NOT listening."
  ret_val=1
fi

r_checkExitStatus $ret_val
