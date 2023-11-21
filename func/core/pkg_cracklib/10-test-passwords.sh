#!/bin/bash
r_log "cracklib" "Test that cracklib can check passwords"

r_log "cracklib" "Test a very simple password"
echo -e "test" | cracklib-check | grep -q "too short"
r_checkExitStatus $?

r_log "cracklib" "Test a simple/dictionary password"
echo -e "testing" | cracklib-check | grep -q "dictionary"
r_checkExitStatus $?

r_log "cracklib" "Testing simplistic password"
echo -e "1234_abc" | cracklib-check | grep -q 'simplistic'
r_checkExitStatus $?

r_log "cracklib" "Testing a complicated password"
echo -e "2948_Obaym-" | cracklib-check | grep -q "OK"
r_checkExitStatus $?
