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
klist 2>&1  | grep -E "(No credentials|Credentials cache .* not found)" &> /dev/null
r_checkExitStatus $?

echo "b1U3OnyX!" | kinit admin@RLIPA.LOCAL

klist | grep "admin@RLIPA.LOCAL" &> /dev/null
r_checkExitStatus $?
