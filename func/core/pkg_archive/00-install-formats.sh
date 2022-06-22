#!/bin/bash
r_log "archive" "Installing appropriate archive formats"

# We might need expect for zmore - does anyone actually use zmore?
p_installPackageNormal bzip2 diffutils gzip less tar unzip util-linux-ng zip lzop
