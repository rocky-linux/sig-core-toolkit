#!/bin/bash
r_log "openssh" "Testing basic login (using sshpass)"
trap 'userdel -rf sshpasstest; unset SSHPASS' EXIT

if sshd -T | grep -q "passwordauthentication yes"; then
  r_log "openssh" "Creating test user"
  export SSHPASS="Blu30nyx!"
  useradd sshpasstest
  echo "${SSHPASS}" | passwd --stdin sshpasstest
  r_log "openssh" "Testing login"
  sshpass -e ssh sshpasstest@localhost echo 'hello'
  r_checkExitStatus $?
else
  r_log "openssh" "Skipping test"
  exit 0
fi
