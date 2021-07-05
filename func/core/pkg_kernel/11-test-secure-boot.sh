#!/bin/bash
r_log "kernel" "Install pesign"
p_installPackageNormal pesign
ARCH=$(uname -m)

if [ "$ARCH" == "x86_64" ]; then
  for k in $(rpm -q kernel --qf "%{version}-%{release}.%{arch}\n"); do
    r_log "kernel" "Validating kernel $k"
    pesign --show-signature --in "/boot/vmlinuz-${k}" | grep -Eq 'Rocky Linux Secure Boot Signing'
    r_checkExitStatus $?
  done
fi
