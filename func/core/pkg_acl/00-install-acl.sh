#!/bin/bash
r_log "acl" "Install the acl package"
p_installPackageNormal acl
r_log "acl" "Remount filesystems with ACL support (this normally should not be needed)"
mount -o remount,acl /
sleep 3
