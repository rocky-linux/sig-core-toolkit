#!/bin/bash
ATTRTEST="/var/tmp/attrtest.img"
ATTRMNT="/mnt/attrtest"

r_log "attr" "Checking that *attr works"
dd if=/dev/zero of="${ATTRTEST}" bs=1024000 count=100 &>/dev/null
r_checkExitStatus $?

mkdir "${ATTRMNT}"
echo -e 'y\n' | mkfs.ext3 "${ATTRTEST}" > /dev/null 2>&1
mount -t ext3 -o loop,user_xattr "${ATTRTEST}" "${ATTRMNT}"
touch "${ATTRMNT}/testfile"
setfattr -n user.test "${ATTRMNT}/testfile"
getfattr "${ATTRMNT}/testfile" | grep -oq "user.test"

r_checkExitStatus $?

# Cleanup
umount /mnt/attrtest
/bin/rm -f "${ATTRTEST}"
/bin/rm -rf "${ATTRMNT}"
