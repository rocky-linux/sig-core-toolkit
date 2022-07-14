#!/bin/bash
if m_getArch aarch64 | grep -qE 'aarch64'; then
  r_log "ipa $0" "Skipping for aarch64"
  exit 0
fi

# The IPA maintainers for EL went a little bonkers with how they want to
# support it. There's two separate modules. It's not clear if in 9 it's
# going to be the same thing or not so this check is there just in case.
if [ "$RL_VER" -eq 8 ]; then
  p_enableModule idm:DL1/{client,common,dns,server}
fi

p_installPackageNormal ipa-server ipa-server-dns expect
