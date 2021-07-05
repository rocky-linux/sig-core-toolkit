#!/bin/bash
r_log "git" "Test basic git clones"

WORKDIR=$(pwd)
TMPREPO=/var/tmp/repo
SHA1=$(echo "Obsidian" | git hash-object --stdin)

r_log "git" "Create bare git repo"
mkdir -p $TMPREPO
# shellcheck disable=SC2164
pushd $TMPREPO
git init . --bare
# shellcheck disable=SC2164
popd

r_log "git" "Clone out"
git clone $TMPREPO cloned

r_log "git" "Configure git user"
# shellcheck disable=SC2164
pushd cloned
git config user.email "obsidian.club@rockylinux.org"
git config user.name "Obsidian Club"

r_log "git" "Add a file and push"
echo "Obsidian" > obsidian
git add obsidian
git commit -m "Obsidian Commit"
git push origin master
# shellcheck disable=SC2164
popd

r_log "git" "Clone out again"
git clone $TMPREPO clone_again
# shellcheck disable=SC2164
pushd clone_again
# shellcheck disable=SC2002
SHA2=$(cat obsidian | git hash-object --stdin)
[ "$SHA1" == "$SHA2" ]
r_checkExitStatus $?

git log --grep="Obsidian Commit" 2>&1
r_checkExitStatus $?

# shellcheck disable=SC2164
popd
# shellcheck disable=SC2086,SC2164
cd $WORKDIR
