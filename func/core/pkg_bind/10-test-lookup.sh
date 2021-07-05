#!/bin/bash
r_log "bind" "Testing bind lookups work"
dig +timeout=5 +short @127.0.0.1 localhost | grep -q "127.0.0.1"
r_checkExitStatus $?
