#!/bin/bash
# Release Engineering Core Functionality Testing
# Louis Abel <label@rockylinux.org> @nazunalika

################################################################################
# Settings and variables

# Exits on any non-zero exit status - Disabled for now.
#set -e
# Undefined variables will cause an exit
set -u

COMMON_EXPORTS='./common/exports.sh'
COMMON_IMPORTS='./common/imports.sh'
SELINUX=$(getenforce)

# End
################################################################################

# shellcheck source=/dev/null
[ -f $COMMON_EXPORTS ] && source $COMMON_EXPORTS || { echo -e "\n[-] $(date): Variables cannot be sourced."; exit 1; }
# shellcheck source=/dev/null
[ -f $COMMON_IMPORTS ] && source $COMMON_IMPORTS || { echo -e "\n[-] $(date): Functions cannot be sourced."; exit 1; }
# Init log
[ -e "$LOGFILE" ] && m_recycleLog || touch "$LOGFILE"
# SELinux check
if [ "$SELINUX" != "Enforcing" ]; then
  echo -e "\n[-] $(date): SELinux is not enforcing."
  exit 1
fi

r_log "internal" "Starting Release Engineering Core Tests"

################################################################################
# Script Work

# Skip tests in a list - some tests are already -x, so it won't be an issue
if [ -e skip.list ]; then
  r_log "internal" "Disabling tests"
  grep -E "^${RL_VER}" skip.list | while read line; do
    testFile=$(echo $line | cut -d '|' -f 2)
    r_log "internal" "SKIP ${testFile}"
    chmod -x ${testFile}
  done
  r_log "internal" "WARNING: Tests above were disabled."
fi

# TODO: should we let $1 judge what directory is ran?
# TODO: get some stacks and lib in there

r_processor <(/usr/bin/find ./core -type f | sort -t'/')
#r_processor <(/usr/bin/find ./lib -type f | sort -t'/')
#r_processor <(/usr/bin/find ./stacks -type f | sort -t'/')

r_log "internal" "Core Tests completed"
exit 0
