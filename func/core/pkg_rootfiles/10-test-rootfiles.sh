#!/bin/bash
r_log "rootfiles" "Test that rootfiles exist"
for y in .bashrc .bash_profile .bashrc .tcshrc .cshrc; do
  r_log "rootfiles" "Checking for $y"
  if [ ! -e "/root/${y}" ]; then
    r_log "rootfiles" "$y doesn't exist"
    r_checkExitStatus 1
  fi
done

r_checkExitStatus 0
