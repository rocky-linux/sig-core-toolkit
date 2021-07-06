#!/bin/bash
r_log "file" "Check image mimetype"
pngFile="$(find /usr/share -type f -name '*.png' -print -quit)"

if [ -z "$pngFile" ]; then
  r_log "file" "No png files were found. SKIP"
  exit 0
fi

file -i "$pngFile" | grep -q 'image/png'
r_checkExitStatus $?
