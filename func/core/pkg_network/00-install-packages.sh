#!/bin/bash
r_log "network" "Install necessary network packages and utilities"
pkgs=(traceroute iputils iproute mtr psmisc net-tools which iptraf)
if [ "$RL_VER" -eq 8 ]; then
  pkgs+=( arpwatch )
fi
p_installPackageNormal "${pkgs[@]}"
