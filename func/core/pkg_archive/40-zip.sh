#!/bin/bash
r_log "archive" "Test zip create and extract"

ZIPDIR="/var/tmp/ziptest"
FILE1="$ZIPDIR/test.1.txt"
FILE2="$ZIPDIR/test.2.txt"

mkdir -p $ZIPDIR
cat > $FILE1 <<EOF
First file!
EOF

cat > $FILE2 <<EOF
Second file!
EOF

/bin/zip -q /var/tmp/zipfile.zip $ZIPDIR/*
/bin/rm -rf $ZIPDIR
if [ -e "$ZIPDIR" ]; then
  r_log "archive" "We couldn't delete $ZIPDIR"
  exit
fi

/bin/unzip -q /var/tmp/zipfile.zip -d /
grep -q 'First file'  $FILE1
RES1=$?
grep -q 'Second file' $FILE2
RES2=$?

if [ $RES1 == 0 ] && [ $RES2 == 0 ]; then
  ret_val=0
fi

r_checkExitStatus $ret_val

/bin/rm -rf /var/tmp/zipfile.zip $ZIPDIR
