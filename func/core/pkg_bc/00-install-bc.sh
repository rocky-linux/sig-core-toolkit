#!/bin/bash
r_log "bc" "Install bc"
p_installPackageNormal bc
r_checkExitStatus $?

r_log "bc" "Check bc version"
bc --version
r_checkExitStatus $?
