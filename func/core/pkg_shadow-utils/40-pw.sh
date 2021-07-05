#!/bin/bash
r_log "shadow" "Check that pwck can use correct files"
pwck -rq ./common/files/correct-passwd ./common/files/correct-shadow
r_checkExitStatus $?

r_log "shadow" "Check that pwck cannot use incorrect files"
pwck -rq ./common/files/incorrect-passwd ./common/files/incorrect-shadow
ret_val=$?
if [ "$ret_val" -eq 0 ]; then
  r_log "shadow" "They're correct."
  exit 1
fi
r_checkExitStatus 0

r_log "shadow" "Check that pwconv is functional"
mkdir -p /var/tmp/pwconv
/bin/cp /etc/shadow /etc/passwd /var/tmp/pwconv || { r_log "shadow" "Could not backup files"; exit 1; }
/bin/cp /var/tmp/pwconv/* /etc
pwconv
r_checkExitStatus $?

r_log "shadow" "Check that pwunconv is functional"
mkdir -p /var/tmp/pwunconv
/bin/cp /etc/passwd /etc/shadow /var/tmp/pwunconv || { r_log "shadow" "Could not backup files"; exit 1; }
/bin/cp /var/tmp/pwunconv/* /etc
pwunconv
r_checkExitStatus $?

# cleanup
pwconv
rm -rf /var/tmp/pwunconv /var/tmp/pwconv
