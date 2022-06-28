#!/bin/bash
r_log "mdadm" "Check that mdadm will operate and return the right exit codes"
[ ${EUID} -eq 0 ] || { r_log "mdadm" "Not running as root. Skipping." ; exit "$PASS"; }
MDADM=$(which mdadm)

[ -z "${MDADM}" ] && { r_log "mdadm" "which reported the binary but it doesn't exist, why?"; exit "$FAIL"; }

${MDADM} --detail --scan &> /dev/null
ret_val=$?

[ "$ret_val" -eq 0 ] || { r_log "mdadm" "There was a non-zero exit. This is likely fatal."; exit "$FAIL"; }

r_checkExitStatus $ret_val
