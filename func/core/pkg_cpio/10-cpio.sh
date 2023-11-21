#!/bin/bash
r_log "cpio" "Test basic cpio stuff"

OUTTER=/var/tmp/cpio/out
INNER=/var/tmp/cpio/in
PASSER=/var/tmp/cpio/pass

trap '/bin/rm -rf /var/tmp/cpio' EXIT

# Nothing should be here. Clean up first.
[ -d /var/tmp/cpio ] && /bin/rm -rf /var/tmp/cpio

r_log "cpio" "Test basic copy out"
mkdir -p "$OUTTER" "$INNER" "$PASSER"

# Ensure at least one file exists in /tmp to prevent errors.
echo 1 > $(mktemp)
# shellcheck disable=2012
find /tmp -type f | cpio -o > "$OUTTER"/cpio.out 2> /dev/null
r_checkExitStatus $?

r_log "cpio" "Test basic copy in"
pushd "$INNER" || exit 1
  cpio -i < "$OUTTER"/cpio.out
  r_checkExitStatus $?
popd || exit 1

r_log "cpio" "Test basic passthrough"
pushd "$INNER" || exit 1
find /tmp | cpio -pd "$PASSER"
r_checkExitStatus $?
popd || exit 1

r_log "cpio" "Checking that the directories (pass and in) are the same"
diff "$PASSER" "$INNER" &> /dev/null
r_checkExitStatus $?
