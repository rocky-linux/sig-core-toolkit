#!/bin/bash
r_log "archive" "Test bzip/bzcat/bunzip"
FILE=/var/tmp/bziptest.txt
trap '/bin/rm -f ${FILE}' EXIT

cat > "$FILE" <<EOF
testing text
EOF

# bzip it up
/bin/bzip2 "$FILE"
/bin/rm -f "$FILE"

# Checking bzcat
if ! bzcat "${FILE}.bz2" | grep -q "testing text"; then
  r_log "archive" "bzcat has failed"
  exit
fi

# bunzip it down
/bin/bunzip2 "${FILE}.bz2"

# check file contents again
grep -q 'testing text' "${FILE}"

r_checkExitStatus $?
