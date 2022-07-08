#!/bin/bash

usage() {
    cat << EOF
$0: prep raw image for azure

usage: $0 raw_image

Description: Takes a raw image and calculates the closest whole-MegaByte,
resizing a copy of the raw image, and returning the path to the resize 'vpc'
image (a .vhd file to upload)

Dumps VHD in \$PWD by default. Override with ``OUTDIR=/path/to/outdir``

Don't try to compress it.
EOF
}

log() {
    local level="$1"; shift
    local msg="$@"
    local out=$([ "$level" == "error" ] && echo 2 || echo 1)
    printf "[%s] %s: %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${level}" "${msg}" >&${out}
    if [[ "${level}" == "error" ]]; then
      exit
    fi
}

MB=$((1024*1024)) # for calculations - 1048576 bytes

if ! command -v qemu-img 2>&1 >/dev/null; then 
    log error "Need qemu-img.";
    usage
    exit
fi

rawdisk="$1"

if [[ -z "$rawdisk" ]]; then
  usage
  log error "need path to a raw image to prep"
fi

outdir="${2:-${PWD}}"

size=$(qemu-img info -f raw --output json "${rawdisk}" | gawk 'match($0, /"virtual-size": ([0-9]+),/, val) {print val[1]}')

rounded_size=$(((($size+$MB-1)/$MB)*$MB)) # size (in bytes) + 1MB, less one, and rounded.

outfilename=$(basename ${rawdisk//body/vhd})
outfile="${outdir}/${outfilename}"
qemu-img resize -f raw "${rawdisk}" "${rounded_size}" || log error "failed to resize"
qemu-img convert -f raw -o subformat=fixed,force_size -O vpc "${rawdisk}" "${outfile}" || log error "failed to convert to VHD format"

echo "${outfile}"
