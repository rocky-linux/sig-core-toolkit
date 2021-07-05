#!/bin/bash
# This is used to help identify what actually failed (assuming we can't figure
# it out ourselves or don't want to run something manually)

for x in success fail; do
  [ -e "$x" ] && rm "$x"
done
