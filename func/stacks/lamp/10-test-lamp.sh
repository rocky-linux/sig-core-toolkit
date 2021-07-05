#!/bin/bash
r_log "lamp" "Testing basic LAMP (not for moths)"
if [ "$RL_VER" -ge 8 ]; then
  SQL=mariadb
else
  SQL=mysqld
fi

r_log "lamp" "Import SQL"
mysql < ./common/files/lamp-sql

cp ./common/files/lamp-sql-php /var/www/html/mysql.php
curl -s http://localhost/mysql.php

r_log "lamp" "Perform the LAMP test (no moths allowed)"
db_content=$(echo "select * from obsidiancore.tests where name='sqltest'" | mysql -B --skip-column-names)

if [ "$db_content" == "sqltest" ]; then
  r_checkExitStatus 0
else
  r_log "lamp" "The database doesn't seem to exist or contain correct data"
  r_checkExitStatus 1
fi

r_log "lamp" "Clean up"
mysql -u root -e 'drop database obsidiancore;'
m_serviceCycler httpd stop
m_serviceCycler $SQL stop
