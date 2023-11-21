#!/bin/bash
r_log "coreutils" "Test hash sum tools"
trap '/bin/rm ${HASHFILE}' EXIT

HASHFILE=/var/tmp/obsidian
echo "Green Obsidian is our release name" > ${HASHFILE}

r_log "coreutils" "Test md5sum"
/usr/bin/md5sum ${HASHFILE} | grep -q 7ee0df0c24cd8fbf747bbeaec2afb935
r_checkExitStatus $?
r_log "coreutils" "Test sha1sum"
/usr/bin/sha1sum ${HASHFILE} | grep -q d9dc0c244c60e6488ebca1733d8072217a2e53d9
r_checkExitStatus $?
r_log "coreutils" "Test sha224sum"
/usr/bin/sha224sum ${HASHFILE} | grep -q 5b7a29dcee3d895e21877d08da1e1408bbd6b09426887cdbfb583753
r_checkExitStatus $?
r_log "coreutils" "Test sha256sum"
/usr/bin/sha256sum ${HASHFILE} | grep -q 38ee9bbdd83f1f1dd4506b061141d956496ab01dd187e24db35e024b37f47110
r_checkExitStatus $?
r_log "coreutils" "Test sha384sum"
/usr/bin/sha384sum ${HASHFILE} | grep -q 5002b880f8b05ab66ead70ea828e3869114fe6a85bffc84fc2199c7d10fee39a69c0b523562e7bb208e7922b0d291916
r_checkExitStatus $?
r_log "coreutils" "Test sha512sum"
/usr/bin/sha512sum ${HASHFILE} | grep -q e50554c29a5cb7bd04279d3c0918e486024c79c4b305a2e360a97d4021dacf56ce0d17fa6e6a0e81ad03d5fb74fbe2d50cce6081c2c277f22b958cdae978a2f5
r_checkExitStatus $?
