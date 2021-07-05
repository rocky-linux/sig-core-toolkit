#!/bin/bash
r_log "git" "Check git installation"
git --version
r_checkExitStatus $?
