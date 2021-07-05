#!/bin/bash
r_log "shadow" "Various User Tests"

# useradd
r_log "shadow" "Ensure that useradd works"
r_log "shadow" "Add the user obsidian"
useradd obsidian
r_checkExitStatus $?

r_log "shadow" "Verify obsidian exists with ID"
id obsidian > /dev/null 2>&1
r_checkExitStatus $?

r_log "shadow" "Verify /etc/passwd"
grep -q "^obsidian" /etc/passwd
r_checkExitStatus $?

# usermod
r_log "shadow" "Verify usermod can add a comment"
usermod -c "Green Obsidian" obsidian
r_checkExitStatus $?
r_log "shadow" "Verify comment exists in /etc/passwd"
grep "^obsidian" /etc/passwd | grep -q "Green Obsidian"
r_checkExitStatus $?
r_log "shadow" "Verify comment exists with getent"
getent passwd obsidian | grep -q "Green Obsidian"
r_checkExitStatus $?

# lastlog
r_log "shadow" "Verify lastlog"
lastlog -u obsidian | grep -q "**Never logged in**"
r_checkExitStatus $?

# chpasswd
r_log "shadow" "Verify chpasswd utility"
chpasswd -e << EOF
obsidian:somenonsense
EOF
r_checkExitStatus $?
r_log "shadow" "Verify /etc/shadow"
grep -q "somenonsense" /etc/shadow
r_checkExitStatus $?

# newusers
r_log "shadow" "Verify newusers utility"
newusers << EOF
blueonyx:x:333344:333344:Blue Onyx:/home/blueonyx:/bin/bash
EOF
r_checkExitStatus $?
r_log "shadow" "Verify blueonyx exists with ID"
id blueonyx > /dev/null 2>&1
r_checkExitStatus $?
r_log "shadow" "Verify /etc/passwd"
grep -q "^blueonyx" /etc/passwd
r_checkExitStatus $?

# chage
r_log "shadow" "Verify chage utility"
echo "obsidian" | passwd --stdin obsidian
chage -d 2012-11-20 obsidian
r_checkExitStatus $?

r_log "shadow" "Verify last password change is correct"
chage -l obsidian | grep Last | grep -q "Nov 20, 2012"
r_checkExitStatus $?

# userdel
r_log "shadow" "Delete the users we created: obsidian"
userdel -rf obsidian
r_checkExitStatus $?
r_log "shadow" "Delete the users we created: blueonyx"
userdel -rf blueonyx
r_checkExitStatus $?

r_log "shadow" "Verify they do not exist"
grep -qE "^obsidian|^blueonyx" /etc/passwd
ret_val=$?
if [ "$ret_val" -ne 0 ]; then
  r_checkExitStatus 0
else
  r_log "shadow" "The users still exist."
  r_checkExitStatus 1
fi
