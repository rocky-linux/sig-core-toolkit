#!/bin/bash
r_log "release" "Ensure the release is actually where it should be"

case $RELEASE_NAME in
  rocky)
    r_log "rocky release" "Base Repo Check"
    grep -q 'name=Rocky' /etc/yum.repos.d/*ocky*.repo
    r_checkExitStatus $?
    r_log "rocky release" "Check /etc/rocky-release"
    grep -q "Rocky" /etc/rocky-release
    r_checkExitStatus $?
    ;;
  centos)
    r_log "centos release" "Base Repo Check"
    grep -q 'name=CentOS' /etc/yum.repos.d/CentOS*-Base*.repo
    r_checkExitStatus $?
    r_log "centos release" "Check /etc/centos-release"
    grep -q "CentOS" /etc/centos-release
    r_checkExitStatus $?
    ;;
  redhat)
    r_log "redhat release" "Base Repo Check"
    grep -q 'name=Red Hat' /etc/yum.repos.d/redhat.repo
    r_checkExitStatus $?
    r_log "redhat release" "Check /etc/redhat-release"
    grep -q "Red Hat" /etc/redhat-release
    r_checkExitStatus $?
    ;;
  *)
    r_log "release" "Not a valid test candidate"
    r_checkExitStatus 1
    ;;
esac
