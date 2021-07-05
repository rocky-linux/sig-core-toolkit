#!/bin/bash
r_log "sqlite" "Test basic table functionality"

r_log "sqlite" "Create a database"
sqlite3 /var/tmp/coretest.db 'drop table if exists tf_coretable'
sqlite3 /var/tmp/coretest.db 'create table tf_coretable(text, id INTEGER);'
r_checkExitStatus $?

r_log "sqlite" "Create a table in that database"
sqlite3 /var/tmp/coretest.db "insert into tf_coretable values ('Green_Obsidian', 1);"
r_checkExitStatus $?

r_log "sqlite" "Check that we can select that table"
sqlite3 /var/tmp/coretest.db "select * from tf_coretable;" | grep -q "Green_Obsidian"
r_checkExitStatus $?
