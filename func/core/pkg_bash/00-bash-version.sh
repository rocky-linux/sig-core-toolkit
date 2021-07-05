#!/bin/bash

# Bash is default installed on minimal
r_log "bash" "Check that the bash version is valid"

bash --version | grep -qE "(x86_64|aarch64|powerpc64le)-redhat-linux-gnu"

r_checkExitStatus $?
