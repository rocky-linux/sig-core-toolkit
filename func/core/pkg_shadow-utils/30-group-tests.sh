#!/bin/bash
r_log "shadow" "Various Group Tests"

r_log "shadow" "Verify /etc/group exists"
[ -e /etc/group ] || { r_log "shadow" "/etc/group doesn't exist"; exit 1; }

# groupadd
r_log "shadow" "Create our first group"
groupadd -g 55553 onyxgroup
r_checkExitStatus $?

# gpasswd
r_log "shadow" "Create a user and add to the group with gpasswd"
useradd onyxuser
gpasswd -a onyxuser onyxgroup
r_checkExitStatus $?

# groupmems
r_log "shadow" "Simple groupmems test against onyxgroup"
groupmems -g onyxgroup -l | grep -q "onyxuser"
r_checkExitStatus $?

# newgrp
r_log "shadow" "Attempt to use newgrp for onyxuser"
groups onyxuser | grep -q "onyxuser onyxgroup" || { r_log "shadow" "Groups information is incorrect."; r_checkExitStatus 1; }
echo $( su - onyxuser << EOF
newgrp onyxgroup
groups
exit
EOF
) | grep -q "onyxgroup onyxuser"
r_checkExitStatus $?

# groupmod
r_log "shadow" "Verify that the onyxgroup exists with GID 55553"
getent group onyxgroup | grep -q "onyxgroup:x:55553:onyxuser"
r_checkExitStatus $?
r_log "shadow" "Change the GID for onyxgroup to 55554"
groupmod -g 55554 onyxgroup
r_checkExitStatus $?

# grpck
r_log "shadow" "Verify grpck functions"
grpck
r_checkExitStatus $?

r_log "shadow" "Check that test files are malformed"
grpck -r ./common/files/malform-group ./common/files/malform-gshadow
ret_val=$?
if [ "$ret_val" -eq 2 ]; then
  r_checkExitStatus 0
else
  r_log "shadow" "Malformed files were not detected."
  r_checkExitStatus 1
fi

# groupdel
r_log "shadow" "Verify groupdel functionality"
getent group onyxgroup > /dev/null 2>&1 || { r_log "shadow" "The onyxgroup doesn't exist."; exit 1; }
groupdel onyxgroup
r_checkExitStatus $?

r_log "shadow" "Make sure that when a group doesn't exist, groupdel returns 6"
groupdel onyxgroup > /dev/null 2>&1
ret_val=$?
if [ "$ret_val" -eq 6 ]; then
  r_checkExitStatus 0
else
  r_log "shadow" "Either the group still existed or another problem occured."
  r_checkExitStatus 1
fi

r_log "shadow" "Make sure that when a group is a primary user group, groupdel returns 8"
groupdel onyxuser
ret_val=$?
if [ "$retval" -eq 8 ]; then
  r_checkExitStatus 0
else
  r_log "shadow" "The group was removed..."
  r_checkExitStatus 1
fi

# grpconv
r_log "shadow" "Test that grpconv properly creates /etc/gshadow"
/bin/cp /etc/gshadow /var/tmp/gshadow.backup
grpconv
r_checkExitStatus $?
r_log "shadow" "Verify the format is consistent"
grpck
r_checkExitStatus $?

# grpunconv
r_log "shadow" "Convert group and gshadow to be merged"
mkdir -p /var/tmp/grpunconv
/bin/cp /etc/group /etc/gshadow /var/tmp/grpunconv
r_log "shadow" "Verify consistency first"
grpck
r_checkExitStatus $?
/bin/cp /var/tmp/grpunconv/* /etc
rm -r /var/tmp/grpunconv
r_log "shadow" "Actually do it."
grpunconv
r_checkExitStatus $?
grpconv

# sg
r_log "shadow" "Test sg"
sg onyxuser "touch /var/tmp/onyxsg"
r_checkExitStatus $?
r_log "shadow" "Verify sg worked"
ls -l /var/tmp/onyxsg | grep -q onyxuser
r_checkExitStatus $?
rm /var/tmp/onyxsg
