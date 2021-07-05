#!/bin/bash
r_log "network" "Install necessary network packages and utilities"
p_installPackageNormal traceroute iputils iproute mtr arpwatch psmisc net-tools which iptraf
