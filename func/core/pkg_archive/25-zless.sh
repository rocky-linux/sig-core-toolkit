#!/bin/bash
r_log "archive" "Testing zless"
r_log "archive" "Generate file"
gzip -cvf /usr/lib/os-release > /var/tmp/gziptest.gz
zless -F /var/tmp/gziptest.gz | grep -q 'Rocky Linux'
r_checkExitStatus $?
