#!/usr/bin/env bash
# 

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "${BASH_SOURCE[0]}")/common"

NAME=gen-torrents

USAGE="usage: $NAME <torrentdir>"
ISODIR=${1}

if [[ -z "${ISODIR}"  || $# == 0 ]]; then
    echo "$USAGE"
    exit
fi

# Setup a lock?
LOCKFILE="/tmp/${NAME}.lock"
if [ -f "$LOCKFILE" ]; then
   echo "Script is already running"
   exit
fi

trap 'rm -f $LOCKFILE' EXIT
touch $LOCKFILE

# stamp the email

# Where to put torrent data
TORRENT_DOWNLOAD_DIR="/opt/rtorrent/download"
# Where to drop created torrents
TORRENT_START_DIR="/opt/rtorrent/watch/start"
# What trackers should be used
TORRENT_TRACKERS=(
    "udp://tracker.opentrackr.org:1337/announce"
    "udp://tracker.openbittorrent.com:80/announce"
)
# Regex of paths to exclude
TORRENT_EXCLUDES='.*\/CHECKSUM.asc'
TORRENT_COMMENT="https://docs.rockylinux.org/release_notes/${REVISION//\./_}/" # dots are bad, mkay?
THREADS=10

printf "* Step 1: Create scaffolding and link\n"
cd "${TORRENT_DOWNLOAD_DIR}" || exit 1
for variant in "${VARIANTS[@]}"; do
    for arch in "${ARCHES[@]}"; do
        # Skip this architecture if it's not there
        if [[ ! -d "${ISODIR}/${arch}" ]]; then
            printf "** %s - Does not exist. Skipping.\n" "${ISODIR}/${arch}"
            continue
        fi

        name_template="Rocky-${REVISION}-${arch}-${variant}"

        if [[ ! -f "${ISODIR}/${arch}/${name_template}.iso" ]]; then
            printf "** %s - Does not exist. Skipping.\n" "${ISODIR}/${arch}/${name_template}.iso"
            continue
        fi

	if [ -d "${name_template}" ]; then continue ; fi
        printf "** Making directory: %s/%s\n" "${TORRENT_DOWNLOAD_DIR}" "${name_template}"
        mkdir "${name_template}" || exit 2

        printf "** Linking Version: %s; Arch: %s; Variant: %s\n" "${REVISION}" "${arch}" "${variant}"
        ln -sv \
            "${ISODIR}"/"${arch}"/{"CHECKSUM"*,"${name_template}".iso*} \
            "${name_template}"/
    done
done


printf "* Step 2: Generate torrents\n"
for torrent_directory in "${TORRENT_DOWNLOAD_DIR}"/Rocky-"${REVISION}"-*; do 
    name="$(basename "${torrent_directory}")"

    if [[ -d "${torrent_directory}" ]]; then 
        printf "** Creating torrent for %s\n" "${torrent_directory}"
    else
        continue
    fi

    torrenttools create                                                                          \
        --announce "${TORRENT_TRACKERS[@]}" --name "${name}"                                     \
        --exclude "${TORRENT_EXCLUDES}" --output "${TORRENT_START_DIR}/${torrent_directory##*/}" \
        --threads "${THREADS}" --comment "${TORRENT_COMMENT}"                                    \
        "${torrent_directory}"
    res=$?
    if [[ $res -ne 0 ]]; then
        printf "**[ERROR] Failed to create torrent."
        exit "$res"
    fi
done
