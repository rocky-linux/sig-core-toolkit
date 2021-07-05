#!/bin/bash
r_log "file" "Install the file package"
# At one point it was installed in an earlier test (or it's default)
m_assertCleanExit rpm -q file
