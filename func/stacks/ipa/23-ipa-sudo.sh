#!/bin/bash
if m_getArch aarch64 | grep -qE 'aarch64'; then
  r_log "ipa -bash" "Skipping for aarch64"
  exit 0
fi

if [ "$IPAINSTALLED" -eq 1 ]; then
  r_log "ipa" "IPA was not successfully installed. Aborting."
  r_checkExitStatus 1
fi

kdestroy -A
klist 2>&1 | grep -E "(No credentials|Credentials cache .* not found)"
r_checkExitStatus $?

echo "b1U3OnyX!" | kinit admin@RLIPA.LOCAL

klist | grep -q "admin@RLIPA.LOCAL"
r_checkExitStatus $?

r_log "ipa" "Creating a test sudo rule"
ipa sudorule-add testrule --desc="Test rule in IPA" --hostcat=all --cmdcat=all --runasusercat=all --runasgroupcat=all &> /dev/null
r_checkExitStatus $?

r_log "ipa" "Adding user to test sudo rule"
ipa sudorule-add-user testrule --users="ipatestuser" &> /dev/null
r_checkExitStatus $?

r_log "ipa" "Verifying rule..."
ipa sudorule-show testrule > /tmp/testrule
grep -q 'Rule name: testrule' /tmp/testrule
r_checkExitStatus $?
grep -q 'Description: Test rule in IPA' /tmp/testrule
r_checkExitStatus $?
grep -q 'Enabled: TRUE' /tmp/testrule
r_checkExitStatus $?
grep -q 'Host category: all' /tmp/testrule
r_checkExitStatus $?
grep -q 'Command category: all' /tmp/testrule
r_checkExitStatus $?
grep -q 'RunAs User category: all' /tmp/testrule
r_checkExitStatus $?
grep -q 'RunAs Group category: all' /tmp/testrule
r_checkExitStatus $?
grep -q 'Users: ipatestuser' /tmp/testrule
r_checkExitStatus $?

m_serviceCycler sssd stop
rm -rf /var/lib/sss/db/*
m_serviceCycler sssd start

sleep 5

r_log "ipa" "Verifying sudo abilities"
sudo -l -U ipatestuser > /tmp/sudooutput
grep -q 'ipatestuser may run the following commands' /tmp/sudooutput
r_checkExitStatus $?
grep -q 'ALL) ALL' /tmp/sudooutput
r_checkExitStatus $?
