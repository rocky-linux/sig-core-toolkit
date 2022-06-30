#!/bin/bash
if m_getArch aarch64 | grep -qE 'aarch64'; then
  r_log "ipa" "Skipping for aarch64"
  exit 0
fi

if [ "$IPAINSTALLED" -eq 1 ]; then
  r_log "ipa" "IPA was not successfully installed. Aborting."
  r_checkExitStatus 1
fi

kdestroy &> /dev/null
klist 2>&1  | grep -E "(No credentials|Credentials cache .* not found)" &> /dev/null
r_checkExitStatus $?

echo "b1U3OnyX!" | kinit admin@RLIPA.LOCAL

klist | grep "admin@RLIPA.LOCAL" &> /dev/null
r_checkExitStatus $?

r_log "ipa" "Adding test service"
ipa service-add testservice/onyxtest.rlipa.local &> /dev/null
r_checkExitStatus $?

r_log "ipa" "Getting keytab for service"
ipa-getkeytab -s onyxtest.rlipa.local -p testservice/onyxtest.rlipa.local -k /tmp/testservice.keytab &> /dev/null
r_checkExitStatus $?

r_log "ipa" "Getting a certificate for service"
ipa-getcert request -K testservice/onyxtest.rlipa.local -D onyxtest.rlipa.local -f /etc/pki/tls/certs/testservice.crt -k /etc/pki/tls/private/testservice.key &> /dev/null
r_checkExitStatus $?

while true; do
  entry="$(ipa-getcert list -r | sed -n '/Request ID/,/auto-renew: yes/p')"
  if [[ $entry =~ "status:"  ]] && [[ $entry =~ "CA_REJECTED"  ]]; then
    r_checkExitStatus 1
    break
  fi
  if [[ $entry =~ ""  ]]; then 
    r_checkExitStatus 0
    break
  fi
  sleep 1
done

while ! stat /etc/pki/tls/certs/testservice.crt &> /dev/null; do
  sync
  sleep 1
done

r_log "ipa" "Verifying keytab"
klist -k /tmp/testservice.keytab | grep "testservice/onyxtest.rlipa.local" &> /dev/null
r_checkExitStatus $?

r_log "ipa" "Verifying key matches the certificate"
diff <(openssl x509 -in /etc/pki/tls/certs/testservice.crt -noout -modulus 2>&1 ) <(openssl rsa -in /etc/pki/tls/private/testservice.key -noout -modulus 2>&1 )
r_checkExitStatus $?

r_log "ipa" "Verifying the certificate against our CA"
openssl verify -CAfile /etc/ipa/ca.crt /etc/pki/tls/certs/testservice.crt | grep "/etc/pki/tls/certs/testservice.crt: OK" &> /dev/null
r_checkExitStatus $?
