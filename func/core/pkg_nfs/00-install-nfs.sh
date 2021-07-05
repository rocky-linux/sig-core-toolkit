#!/bin/bash
r_log "nfs" "Install nfs and autofs utilities"
p_installPackageNormal autofs nfs-utils rpcbind
