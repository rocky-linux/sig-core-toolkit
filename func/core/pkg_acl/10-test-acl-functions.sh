#!/bin/bash
ACLFILE=/tmp/testfile_acl
r_log "acl" "Test that the acl get and set functions work"
touch "${ACLFILE}"
trap '/bin/rm -f ${ACLFILE}' EXIT

# Use setfacl for readonly
r_log "acl" "Set readonly ACL for the user nobody"
setfacl -m user:nobody:r "${ACLFILE}"

# Use getfacl to verify readonly
r_log "acl" "Verifying that the nobody user is set to read only"
getfacl "${ACLFILE}" | grep -q 'user:nobody:r--'

r_checkExitStatus $?
