#!/bin/bash
r_log "firewalld" "Check that the default zone is public"
firewall-cmd --get-active-zones | grep -q public
r_checkExitStatus $?

r_log "firewalld" "Check that a default service is open"
firewall-cmd --list-services | grep -q ssh
r_checkExitStatus $?
