#!/bin/bash
r_log "acl" "Install the acl package"
p_installPackageNormal acl
p_installPackageNormal attr
# This normally is not needed.
#r_log "acl" "Remount filesystems with ACL support"
#mount -o remount,acl /
sleep 3
