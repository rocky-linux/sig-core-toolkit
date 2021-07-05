#!/bin/bash
r_log "selinux" "Install selinux toolset"

# Shouldn't change in 9
p_installPackageNormal python3-libselinux
