#!/bin/bash
if m_getArch aarch64 | grep -qE 'aarch64'; then
  r_log "ipa $0" "Skipping for aarch64"
  exit 0
fi

if [ "$IPAINSTALLED" -eq 1  ]; then
  r_log "ipa" "IPA was not successfully installed. Aborting."
  r_checkExitStatus 1
fi

kdestroy &> /dev/null
klist 2>&1 | grep -E "(No credentials|Credentials cache .* not found)" &> /dev/null
r_checkExitStatus $?

echo "b1U3OnyX!" | kinit admin@RLIPA.LOCAL

klist | grep "admin@RLIPA.LOCAL" &> /dev/null
r_checkExitStatus $?

r_log "ipa" "Test adding a user"
ipa user-add --first=test --last=user --random ipatestuser > /tmp/ipatestuser
grep -q 'Added user "ipatestuser"' /tmp/ipatestuser

ret_val=$?
if [ "$ret_val" -ne 0 ]; then
  r_log "ipa" "User was not created, this is considered fatal"
  r_checkExitStatus 1
  exit 1
fi

sed -i 's|^  ||g' /tmp/ipatestuser
grep -q 'First name: test' /tmp/ipatestuser
r_checkExitStatus $?
grep -q 'Last name: user' /tmp/ipatestuser
r_checkExitStatus $?
grep -q 'Full name: test user' /tmp/ipatestuser
r_checkExitStatus $?
grep -q 'Home directory: /home/ipatestuser' /tmp/ipatestuser
r_checkExitStatus $?

r_log "ipa" "Changing password of the user"
kdestroy &> /dev/null
userPassword="$(awk '/Random password/ { print $3 }' /tmp/ipatestuser)"
/bin/rm /tmp/ipatestuser

expect -f -  <<EOF
set send_human {.1 .3 1 .05 2}
spawn kinit ipatestuser
sleep 1
expect "Password for ipatestuser@RLIPA.LOCAL: "
send -h -- "$(echo "$userPassword")\r"
sleep 1
expect "Enter new password: "
send -h -- "gr@YAm3thy5st!\r"
sleep 1
expect "Enter it again: "
send -h -- "gr@YAm3thy5st!\r"
sleep 5
close
EOF

r_log "ipa" "Re-doing a kinit"
expect -f - <<EOF
set send_human {.1 .3 1 .05 2}
spawn kinit ipatestuser
sleep 1
expect "Password for ipatestuser@C6IPA.LOCAL:"
send -h "gr@YAm3thy5st!\r"
sleep 1
close
EOF

klist | grep "ipatestuser@RLIPA.LOCAL" &> /dev/null
r_checkExitStatus $?

kdestroy &> /dev/null

r_log "ipa" "Testing for user in getent"
getent passwd ipatestuser &> /dev/null
r_checkExitStatus $?
