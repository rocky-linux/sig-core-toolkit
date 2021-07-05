#!/bin/bash
r_log "perl" "Test perl script"
echo 'print "Hello!"' > /var/tmp/perltest
perl /var/tmp/perltest | grep -q "Hello!"
r_checkExitStatus $?
