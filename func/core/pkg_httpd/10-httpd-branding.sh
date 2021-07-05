#!/bin/bash
r_log "httpd" "Verify httpd branding"

r_log "httpd" "Token"
curl -sI http://localhost/ | grep -i "Server:\ Apache.*\ (Rocky)" > /dev/null 2>&1
r_checkExitStatus $?

r_log "httpd" "index"
curl -sI http://localhost/ | grep -i "Rocky" > /dev/null 2>&1
r_checkExitStatus $?
