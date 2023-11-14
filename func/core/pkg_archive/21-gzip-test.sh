#!/bin/bash
r_log "archive" "Test gzip/zcat/gunzip"

FILE=/var/tmp/gzip-test.txt
MD5HASH=e6331c582fbad6653832860f469f7d1b

# clean up
trap '/bin/rm $FILE* &> /dev/null && /bin/rm -rf /var/tmp/gziptest &> /dev/null' EXIT

# Double check that stuff is cleared out
/bin/rm $FILE* &> /dev/null
/bin/rm -rf /var/tmp/gziptest &> /dev/null

# Make our test file
cat > $FILE <<EOF
Green Obsidian is the release name
EOF

# gzip
r_log "archive" "Testing gzip works"
gzip $FILE || r_checkExitStatus 1

# zcat
r_log "archive" "Test zcat works"
zcat $FILE.gz | grep -q "Green Obsidian" || r_checkExitStatus 1

# no overwrite
r_log "archive" "Check that files won't be overwritten"
touch $FILE
echo | gunzip $FILE &> /dev/null
[ $? -ne 2 ] && r_checkExitStatus 1

echo | gzip $FILE &> /dev/null
[ $? -ne 2 ] && r_checkExitStatus 1

# force overwrite
r_log "archive" "Check that files can be forcefully overwritten"
gunzip -f $FILE.gz || r_checkExitStatus 1
touch $FILE.gz
gzip -f $FILE || r_checkExitStatus 1

# -a should be ignored
# Hopefully this behavior does NOT change in 9
r_log "archive" "Check that -a is ignored"
gunzip -a $FILE.gz 2>&1 | head -n 1 | grep -q 'gzip: option --ascii ignored on this system' || r_checkExitStatus 1

# -c should write to stdout
r_log "archive" "Check that -c outputs to stdout"
gzip -c $FILE | gunzip | grep -q 'Green Obsidian' || r_checkExitStatus 1

# Expected hash is: e6331c582fbad6653832860f469f7d1b
# check -l
r_log "archive" "Check that the md5 matches"
gzip $FILE
md5check=$(gzip -l $FILE.gz | md5sum | cut -d' ' -f1)
[ "$md5check" == "$MD5HASH" ] || r_checkExitStatus 1

# Check that -v gives us some good info
r_log "archive" "Check that -v increases verbosity"
gzip -lv $FILE.gz | grep -q "e0e1ed1a" || r_checkExitStatus 1
gunzip $FILE.gz

# custom suffix
r_log "archive" "Check that a custom suffix can be used"
gzip -S .rl $FILE
[ -e $FILE.rl ] || r_checkExitStatus 1
gunzip -S .rl $FILE || r_checkExitStatus 1

# check -r
r_log "archive" "Check that -r functions"
mkdir /var/tmp/gziptest
touch /var/tmp/gziptest/{a,b}
gzip -r /var/tmp/gziptest
[ "$(find /var/tmp/gziptest/*.gz | wc -l)" -eq "2" ] || r_checkExitStatus 1

# check different compression levels
r_log "archive" "Check compression levels"
cp $FILE $FILE.1
gzip -1 $FILE
gzip -9 $FILE.1
[ "$(stat -c %s $FILE.gz)" -ne "$(stat -c %s $FILE.1.gz)" ] || r_checkExitStatus 1

# check multiple input files
r_log "archive" "Check multiple input files"
gunzip $FILE.gz $FILE.1.gz || r_checkExitStatus 1

# don't specify an extension
r_log "archive" "Don't specify file extensions"
gzip $FILE $FILE.1 || r_checkExitStatus 1

# check that .Z can be handled
r_log "archive" "Verify that .Z files can be handled"
gunzip $FILE.gz
ls -l /var/tmp >> $FILE
if [ "$RL_VER" -eq 8 ]; then
  compress $FILE || r_checkExitStatus 1
  gunzip $FILE.Z || r_checkExitStatus 1
else
  r_log "archive" "Skipping for 9"
fi

# handle some zip files
r_log "archive" "Verify that .zip files can be handled"
zip $FILE.zip $FILE &> /dev/null || r_checkExitStatus 1
gunzip -f -S .zip $FILE.zip || r_checkExitStatus 1

# handle some tgz files
r_log "archive" "Verify that .tgz files can be handled"
tar -czf $FILE.tgz $FILE &> /dev/null
gunzip $FILE.tgz
[ -e $FILE.tar ]
r_checkExitStatus $?
