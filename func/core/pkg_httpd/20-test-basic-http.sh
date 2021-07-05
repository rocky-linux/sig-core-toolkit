#!/bin/bash
r_log "httpd" "Test basic http functionality"
curl -H 'Accept-Language: en' -s http://localhost/ | grep "Test Page" > /dev/null 2>&1
r_checkExitStatus $?
