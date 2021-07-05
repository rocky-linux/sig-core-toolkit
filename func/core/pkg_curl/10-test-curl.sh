#!/bin/bash
r_log "curl" "Basic curl test"

# TODO: Setup variables/switches I guess? Would need to be utilized in primary
#       script

STRING="Rocky Linux"
URL="https://rockylinux.org"

r_log "curl" "Checking out ${URL}"

curl --location -s ${URL} | grep -q "${STRING}"
