#!/bin/bash
ACLIMG=/tmp/testacl.img
r_log "acl" "Test the use of xattr"
touch "${ACLIMG}"
trap '/bin/rm -f ${ACLIMG}' EXIT

# Use setfacl for readonly
r_log "acl" "Create image"
dd if=/dev/zero of=${ACLIMG} bs=1024000 count=100
echo -e 'y\n' | mkfs.ext3 "${ACLIMG}"
mkdir /mnt/xattr
mount -t ext3 -o loop,user_xattr "${ACLIMG}" /mnt/xattr
touch /mnt/xattr/testfile

r_log "acl" "Apply attrs as needed"
setfattr -n user.nobody /mnt/xattr/testfile
getfattr /mnt/xattr/testfile | grep -q 'user.nobody'
final_status=$?

umount /mnt/xattr

r_checkExitStatus $final_status
