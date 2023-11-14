#!/bin/bash
r_log "archive" "Test tar create and extract"

TARDIR="/var/tmp/tartest"
FILE1="$TARDIR/test.1.txt"
FILE2="$TARDIR/test.2.txt"
trap '/bin/rm -rf /var/tmp/tarfile.tar $TARDIR' EXIT

mkdir -p $TARDIR
cat > $FILE1 <<EOF
First file!
EOF

cat > $FILE2 <<EOF
Second file!
EOF

/bin/tar -c $TARDIR -f /var/tmp/tarfile.tar > /dev/null 2>&1
/bin/rm -rf $TARDIR
if [ -e "$TARDIR" ]; then
  r_log "archive" "We couldn't delete $TARDIR"
  exit
fi

tar -C / -xf /var/tmp/tarfile.tar
grep -q 'First file'  $FILE1
RES1=$?
grep -q 'Second file' $FILE2
RES2=$?

if [ $RES1 == 0 ] && [ $RES2 == 0 ]; then
  ret_val=0
fi

r_checkExitStatus $ret_val
