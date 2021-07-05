#!/bin/bash
r_log "dnf" "Install ksh package"
p_installPackageNormal ksh

r_log "dnf" "Remove ksh package"
p_removePackage ksh

rpm -q ksh | grep -q "package ksh is not installed"
r_checkExitStatus $?
