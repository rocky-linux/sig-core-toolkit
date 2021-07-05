#!/bin/bash
r_log "selinux" "Check policy mismatch"

cat << EOF | /usr/bin/python3 -
import sys
import selinux.audit2why as audit2why

try:
    audit2why.init()
except:
    sys.exit(1)

sys.exit(0)
EOF

r_checkExitStatus $?
