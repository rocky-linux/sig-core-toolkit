#!/bin/bash
r_log "secureboot" "Verify that grub2-efi is correctly signed"

if [ ! -d /sys/firmware/efi ]; then
  r_log "secureboot" "System was not booted in EFI mode. It is likely that grub2-efi is also not installed."
  if [ -f /boot/efi/EFI/rocky/grubx64.efi ]; then
    r_log "secureboot" "Correct, system is not EFI and thus does not have grub2-efi installed."
    exit 0
  fi
else
  if [[ "$rl_arch" == "x86_64" ]]; then
    p_installPackageNormal pesign
    pesign --show-signature --in /boot/efi/EFI/rocky/shim.efi | grep -Eq "Microsoft Windows UEFI Driver Publisher"
    r_checkExitStatus $?
  else
    r_log "secureboot" "x86_64 is the only supported secureboot arch at this time"
    exit 0
  fi
fi
