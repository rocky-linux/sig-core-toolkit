#!/bin/bash
r_log "archive" "Checking gzexe"
r_log "archive" "Creating archive"
FILE=/var/tmp/gzexe-test-script
trap '/bin/rm -f $FILE* 2>/dev/null' EXIT

/bin/rm -f $FILE* &>/dev/null

cat > $FILE <<EOF
#!/bin/bash
echo "Hello!"
EOF

chmod +x $FILE
$FILE | grep -q "Hello!" || r_checkExitStatus 1

r_log "archive" "Test gzexe"
/bin/gzexe $FILE &>/dev/null || r_checkExitStatus 1

r_log "archive" "Check that it actually runs"
$FILE | grep -q "Hello!"
r_checkExitStatus $?
