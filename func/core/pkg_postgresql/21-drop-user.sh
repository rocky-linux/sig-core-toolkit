#!/bin/bash
r_log "postgresql" "Dropping user"
su - postgres -c 'dropuser testuser' > /dev/null 2>&1
r_checkExitStatus $?
