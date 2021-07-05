#!/bin/bash
r_log "rocky" "Check the GPG keys"
file /etc/pki/rpm-gpg/RPM-GPG-KEY-rockyofficial > /dev/null 2>&1 && \
  file /etc/pki/rpm-gpg/RPM-GPG-KEY-rockytesting > /dev/null 2>&1

r_checkExitStatus $?
