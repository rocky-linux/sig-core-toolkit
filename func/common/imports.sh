#!/bin/bash
# Common functions and imports to use across all scripts
# Louis Abel <label@rockylinux.org> @nazunalika

################################################################################
# Functions that (r)eturn things
function r_log() {
  SCR=$1
  MESSAGE=$2
  printf "[-] %s %s: %s\n" "$(date +'%m-%d-%Y %T')" "$SCR" "$MESSAGE" >> "$LOGFILE"
}

# Always call this at the end of scripts to check for exit status. This will
# report "PASS" or "FAIL" depending on the exit and it will show up in the log.
# Args: $1 will be whatever you want checked
function r_checkExitStatus() {
  [ "$1" -eq 0 ] && r_log "result" "PASSED" && return "$PASS"
  r_log "status" "FAILED"
  exit "$FAIL"
}

# Processes a list of folders containing the tests. This ignores files that
# start with a dot (.), an underscore (_) or contain README in the name.
# This is done because we cannot guarantee that whoever adds in tests or
# writes additional "find" commands won't negate these lookups.

# Additionally, we should look at the file's executable status. I considered
# just having the files named differently, but that seemed more annoying than
# just setting +x
function r_processor() {
  # shellcheck disable=SC2068
  exec 8< $@
  # shellcheck disable=SC2162
  while read -u 8 file; do
    # shellcheck disable=SC2086
    if [[ "$(basename ${file})" =~ README|^\.|^_ ]]; then
      continue
    fi
    [ -x "${file}" ] && echo "Begin processing script: ${file}" && "${file}"
  done
  return 0
}

function r_checkEPELEnabled() {
  /usr/bin/dnf repolist | grep -q '^epel'
  return $?
}

################################################################################
# Functions that deal with (p)ackages

# Installs packages normally (including weak dependencies)
# Args: Any number of $1..X
function p_installPackageNormal() {
  r_log "internal" "Attempting install: $*"
  # shellcheck disable=SC2086
  /usr/bin/dnf --assumeyes --debuglevel ${DNFDEBUG} install "$@"
  r_checkExitStatus $?
}

# Installs packages excluding weak dependencies - There are some cases where
# you would need to do this.
# Args: Any number of $1..X
function p_installPackageNoWeaks() {
  r_log "internal" "Attempting install: $*"
  # shellcheck disable=SC2086
  /usr/bin/dnf --assumeyes --debuglevel ${DNFDEBUG} --setopt install_weak_deps=0 install "$@"
  r_checkExitStatus $?
}

# Removes packages
# Args: Any number of $1..X
function p_removePackage() {
  r_log "internal" "Attempting uninstall: $*"
  # shellcheck disable=SC2086
  /usr/bin/dnf --assumeyes --debuglevel ${DNFDEBUG} remove "$@"
  r_checkExitStatus $?
}

# Enables dnf modules
# Args: Any number of $1..X
function p_enableModule() {
  r_log "internal" "Enabling module: $*"
  # shellcheck disable=SC2086
  /usr/bin/dnf --assumeyes --debuglevel ${DNFDEBUG} module enable "$@"
  r_checkExitStatus $?
}

# Resets modules (since you can't "disable" technically)
# Args: Any number of $1..X
function p_resetModule() {
  r_log "internal" "Resetting module: $*"
  # shellcheck disable=SC2086
  /usr/bin/dnf --assumeyes --debuglevel ${DNFDEBUG} module reset "$@"
  r_checkExitStatus $?
}

function p_getPackageRelease() {
  rpm -q --queryformat '%{RELEASE}' "$1"
}

function p_getPackageArch() {
  rpm -q --queryformat '%{ARCH}' "$1"
}

function p_getDist() {
  rpm -q "$(rpm -qf /etc/redhat-release)" --queryformat '%{version}\n' | cut -d'.' -f1
}

################################################################################
# Functions that that are considered (m)isc

# Service cycler, basically a way of handling services and also being able to
# prevent potential race conditions.
function m_serviceCycler() {
  if [ "$2" = "cycle" ]; then
    # shellcheck disable=SC2086
    /bin/systemctl stop $1
    sleep 3
    # shellcheck disable=SC2086
    /bin/systemctl start $1
  else
    # shellcheck disable=SC2086
    /bin/systemctl $2 $1
  fi
  sleep 3
}

function m_checkForPort() {
  while true; do
    sleep 1
    # shellcheck disable=SC2086
    if echo > /dev/tcp/localhost/$1 >/dev/null 2>&1; then
      r_log "internal" "Waiting for TCP port $1 to start listening"
      break
    fi
  done
}

function m_assertCleanExit() {
  "$@" > /dev/null 2>&1
  r_checkExitStatus $?
}

function m_assertEquals() {
  [ "$1" -eq "$2" ]
  r_checkExitStatus $?
}

function m_skipReleaseEqual() {
  if [ "$(rpm --eval %rhel)" -eq "$1" ]; then
    r_log "$2" "Skipped test for $1 release"
    exit 0
  fi
}

function m_skipReleaseNotEqual() {
  if [ "$(rpm --eval %rhel)" -ne "$1" ]; then
    r_log "$2" "Skipped test"
    exit 0
  fi
}

function m_skipReleaseGreaterThan() {
  if [ "$(rpm --eval %rhel)" -gt "$1" ]; then
    r_log "$2" "Skipped test"
    exit 0
  fi
}

function m_skipReleaseLessThan() {
  if [ "$(rpm --eval %rhel)" -lt "$1" ]; then
    r_log "$2" "Skipped test"
    exit 0
  fi
}

function m_selectAlternative() {
  primaryName=$1
  searchRegex=$2
  option=$(/bin/echo | /usr/sbin/alternatives --config "$primaryName" | /bin/grep -E "$searchRegex" | /usr/bin/head -n1 | sed 's/    .*//g;s/[^0-9]//g')
  if [ -z "$option" ]; then
    r_log "alternatives" "Option not found for alternative $searchRegex of $primaryName"
    r_checkExitStatus 1
  fi
  r_log "alternatives" "Selecting alternative $option for $primaryName $searchRegex"
  /bin/echo "$option" | /usr/sbin/alternatives --config "$primaryName" > /dev/null 2>&1
}

function m_getArch() {
  /usr/bin/uname -m
}

function m_recycleLog() {
  num=0
  rotFile="${LOGFILE}.$num"
  while [ -e "$rotFile" ]; do
    num=$(( num + 1 ))
    rotFile="${LOGFILE}.$num"
  done
  mv "$LOGFILE" "$rotFile"
}

################################################################################
# export all functions below

# When this is sourced, the functions are typically already available and ready
# to be used. But it does not hurt to have them below.

rl_ver=$(p_getDist)
rl_arch=$(m_getArch)
export rl_ver
export rl_arch

export -f r_log
export -f r_checkExitStatus
export -f r_processor
export -f r_checkEPELEnabled
export -f p_installPackageNormal
export -f p_installPackageNoWeaks
export -f p_removePackage
export -f p_enableModule
export -f p_resetModule
export -f p_getPackageRelease
export -f p_getPackageArch
export -f p_getDist
export -f m_serviceCycler
export -f m_checkForPort
export -f m_assertCleanExit
export -f m_assertEquals
export -f m_skipReleaseEqual
export -f m_skipReleaseNotEqual
export -f m_skipReleaseGreaterThan
export -f m_skipReleaseLessThan
export -f m_selectAlternative
export -f m_getArch
export -f m_recycleLog
