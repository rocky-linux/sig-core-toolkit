#!/bin/bash
r_log "annobin" "Ensure a simple program builds with gcc annobin"
OUTPUTPROG=$(mktemp)

r_log "annobin" "Build program with gcc"
gcc -x c -specs=/usr/lib/rpm/redhat/redhat-hardened-cc1 \
  -specs=/usr/lib/rpm/redhat/redhat-annobin-cc1 \
  -o "${OUTPUTPROG}" ./common/files/hello.c

# Must match exactly
r_log "annobin" "Verify the program works"
"${OUTPUTPROG}" | grep -q "Hello!"
r_checkExitStatus $?

/bin/rm -f "${OUTPUTPROG}"
