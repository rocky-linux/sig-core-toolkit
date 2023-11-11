#!/bin/bash

diff -y /tmp/list_a /tmp/list_b | grep '|' > /tmp/diffs
sed -e 's/\t//g' -e 's/ //g' /tmp/diffs > /tmp/endgame
echo "Cleaned table in /tmp/endgame"
