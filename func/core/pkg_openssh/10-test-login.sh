#!/bin/bash
r_log "openssh" "Testing basic login (using sshpass)"

if sshd -T | grep -q "passwordauthentication yes"; then
  r_log "openssh" "Creating test user"
  SSHPASS="Blu30nyx!"
  useradd sshpasstest
  echo "${SSHPASS}" | passwd --stdin sshpasstest
  r_log "openssh" "Testing login"
  sshpass -e ssh sshpasstest@localhost echo 'hello'
  r_checkExitStatus $?
  userdel -rf sshpasstest
else
  r_log "openssh" "Skipping test"
  exit 0
fi
