#!/bin/bash
r_log "sqlite" "Test that we can dump the database"
sqlite3 /var/tmp/coretest.db ".dump" | grep -q "Green_Obsidian"
r_checkExitStatus $?
