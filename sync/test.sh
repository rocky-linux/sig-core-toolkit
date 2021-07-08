#!/bin/bash
# tests that the variables work
# shellcheck disable=SC1090
source "$(dirname "$0")/common"
echo "${RELEASE_DIR}"
echo "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}"
echo "$NONMODS_REPOS"
echo "${REV}"
