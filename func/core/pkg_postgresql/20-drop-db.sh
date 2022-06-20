#!/bin/bash
r_log "postgresql" "Dropping database"
su - postgres -c 'dropdb pg_test' > /dev/null 2>&1
r_checkExitStatus $?
