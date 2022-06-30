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

expect -f - <<EOF
set send_human {.1 .3 1 .05 2}
spawn kinit admin
sleep 1
expect "Password for admin@RLIPA.LOCAL:"
send -h "b1U3OnyX!\r"
sleep 5
close
EOF

klist | grep "admin@RLIPA.LOCAL" &> /dev/null
r_checkExitStatus $?
