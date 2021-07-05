#!/bin/bash
r_log "httpd" "Test basic https functionality"
curl -H 'Accept-Language: en' -ks https://localhost/ | grep "Test Page" > /dev/null 2>&1
r_checkExitStatus $?
