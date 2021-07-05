#!/bin/bash
r_log "archive" "Verifying gzip binaries"

for bin in gunzip gzexe gzip zcat zcmp zdiff zegrep zfgrep zforce zgrep zless zmore znew; do
  echo -n "$bin"
  r_log "archive" "$bin"
  $bin --version &> /dev/null || r_checkExitStatus 1
done

echo

r_checkExitStatus 0
