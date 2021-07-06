#!/bin/bash
# Performs a full on sync of a minor release, directories and all. It calls the
# other scripts in this directory to assist.
# Source common variables
# shellcheck disable=SC2046,1091,1090
source $(dirname "$0")/common

# sync all pieces of a release, including extras, nfv, etc

# move around the ISOs a bit, make things comfortable
