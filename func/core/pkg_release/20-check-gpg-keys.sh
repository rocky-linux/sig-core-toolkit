#!/bin/bash
r_log "rocky" "Check the GPG keys"
if [ "$RL_VER" -eq 8  ]; then
  file /etc/pki/rpm-gpg/RPM-GPG-KEY-rockyofficial > /dev/null 2>&1 && \
    file /etc/pki/rpm-gpg/RPM-GPG-KEY-rockytesting > /dev/null 2>&1
else
  file "/etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-${RL_VER}" > /dev/null 2>&1 && \
    file "/etc/pki/rpm-gpg/RPM-GPG-KEY-Rocky-${RL_VER}-Testing" > /dev/null 2>&1
fi

r_checkExitStatus $?
