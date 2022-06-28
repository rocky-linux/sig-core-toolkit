#!/bin/bash
r_log "postgresql" "Creating db"
su - postgres -c 'createdb pg_test'
r_checkExitStatus $?
