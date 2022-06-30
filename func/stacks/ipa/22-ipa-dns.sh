#!/bin/bash
if m_getArch aarch64 | grep -qE 'aarch64'; then
  r_log "ipa -bash" "Skipping for aarch64"
  exit 0
fi

if [ "$IPAINSTALLED" -eq 1 ]; then
  r_log "ipa" "IPA was not successfully installed. Aborting."
  r_checkExitStatus 1
fi

kdestroy &> /dev/null
klist 2>&1  | grep -qE "(No credentials|Credentials cache .* not found)" &> /dev/null
r_checkExitStatus $?

echo "b1U3OnyX!" | kinit admin@RLIPA.LOCAL

klist | grep "admin@RLIPA.LOCAL" &> /dev/null
r_checkExitStatus $?

r_log "ipa" "Adding testzone subdomain"
ipa dnszone-add --name-server=rltest.rlipa.local. --admin-email=hostmaster.testzone.rlipa.local. testzone.rlipa.local &> /dev/null
r_checkExitStatus $?
sleep 5

r_log "ipa" "Get SOA from testzone subdomain"
dig @localhost SOA testzone.rlipa.local | grep -q "status: NOERROR" &> /dev/null
r_checkExitStatus $?

r_log "ipa" "Adding a CNAME record to the primary domain"
ipa dnsrecord-add rlipa.local testrecord --cname-hostname=rltest &> /dev/null
r_checkExitStatus $?
sleep 5

r_log "ipa" "Retrieving CNAME record"
dig @localhost CNAME testrecord.rlipa.local | grep -q "status: NOERROR" &> /dev/null
r_checkExitStatus $?

r_log "ipa" "Adding a CNAME to subdomain"
ipa dnsrecord-add testzone.rlipa.local testrecord --cname-hostname=rltest.rlipa.local. &> /dev/null
r_checkExitStatus $?
sleep 5

r_log "ipa" "Testing can retrieve record from subdomain"
dig @localhost CNAME testrecord.testzone.rlipa.local | grep -q "status: NOERROR" &> /dev/null
r_checkExitStatus $?
