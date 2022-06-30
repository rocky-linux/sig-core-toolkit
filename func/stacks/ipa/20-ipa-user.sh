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
userDetails="$(ipa user-add --first=test --last=user --random ipatestuser)"
echo "$userDetails" | grep -q 'Added user "ipatestuser"'
r_checkExitStatus $?

echo "$userDetails" | grep -q 'First name: test'
r_checkExitStatus $?
echo "$userDetails" | grep -q 'Last name: user'
r_checkExitStatus $?
echo "$userDetails" | grep -q 'Full name: test user'
r_checkExitStatus $?
echo "$userDetails" | grep -q 'Home directory: /home/ipatestuser'
r_checkExitStatus $?

r_log "ipa" "Changing password of the user"
kdestroy &> /dev/null

expect -f -  <<EOF
set send_human {.1 .3 1 .05 2}
spawn kinit ipatestuser
sleep 1
expect "Password for ipatestuser@RLIPA.LOCAL: "
send -h -- "$(echo "$userDetails" | awk '$0 ~ /Random password/ {print $3}')\r"
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
