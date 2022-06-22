#!/bin/bash
# Common Variables
export DNFDEBUG=0
export readonly PASS=0
export readonly FAIL=1
RL_VER=$(rpm --eval %rhel)
export readonly RL_VER
export readonly PRE_RELEASE=0
# This should be either: rocky, redhat, centos
export readonly RELEASE_NAME=rocky
# A 0 means it was successful. It can be changed to 1 on failure.
export IPAINSTALLED=0

LOGFILE="$(pwd)/log/$(date +'%m-%d-%Y')-tests.log"
export LOGFILE
