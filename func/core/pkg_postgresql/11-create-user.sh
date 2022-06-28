#!/bin/bash
r_log "postgresql" "Creating user"
su - postgres -c 'createuser -S -R -D testuser' > /dev/null 2>&1
r_checkExitStatus $?
