#!/bin/bash
if m_getArch aarch64 | grep -qE 'aarch64'; then
  r_log "ipa" "Skipping for aarch64"
  exit 0
fi

r_log "ipa" "Setting up the networking portions of the system"
net_int=$(ip addr | grep -B1 "link/ether" | head -n 1 | awk '{print $2}' | tr -d ':')
net_ip=$(ip -4 -o addr show dev "${net_int}" | awk '/inet/ {print $4}' | cut -d'/' -f1)
forwarder=$(awk '$0 ~ /nameserver/ {print $2}' /etc/resolv.conf | head -n 1)

r_log "ipa" "Set hostname"
hostnamectl set-hostname onyxtest.rlipa.local
echo "$net_ip $(hostname)" >> /etc/hosts
hostname | grep "onyxtest.rlipa.local" &> /dev/null
r_checkExitStatus $?

r_log "ipa" "Installing the IPA domain (warning this takes a while)"
ipa-server-install -U \
  --hostname="$(hostname)" \
  --ip-address="${net_ip}" \
  -r RLIPA.LOCAL \
  -n rlipa.local \
  -p b1U3OnyX! \
  -a b1U3OnyX! \
  --ssh-trust-dns \
  --setup-dns \
  --mkhomedir \
  --forwarder="${forwarder}"

ret_val=$?

if [ "$ret_val" -eq 0 ]; then
  r_log "ipa" "IPA Domain installed"
  r_checkExitStatus 0
else
  r_log "ipa" "IPA Domain failed to install"
  r_checkExitStatus 1
  export IPAINSTALLED=1
fi
