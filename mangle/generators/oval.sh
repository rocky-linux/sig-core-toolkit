#!/bin/bash

log(){
  printf "[LOG] [%s] %s\n" "$(date -Is)" "$1"
}

OUTPUT_DIR=/mnt/repos-staging/mirror/pub/oval
TEMP="$(mktemp -d)"

for version in 8 9; do
  file="$TEMP/org.rockylinux.rlsa-$version.xml"
  log "Generating $file"
  #podman run --rm --storage-opt ignore_chown_errors=true ghcr.io/rocky-linux/oval:latest -- $version > "$file"
  # The above reports an error when running on R8. The below may *not* work on anything else.
  # TODO: verify this is the case.
  podman run --rm --storage-opt ignore_chown_errors=true ghcr.io/rocky-linux/oval:latest $version > "$file"
  log "Compressing $file to $file.bz"
  bzip2 -kfz "$file"
done

log "Generating checksums"

pushd "$TEMP" >/dev/null || exit 2

# shellcheck disable=2035
sha256sum --tag * > CHECKSUM
popd > /dev/null || exit 2

log "Copying to staging directory $TEMP => $OUTPUT_DIR"
sudo rsync -vrSHP "$TEMP/" "$OUTPUT_DIR"
sudo chown -Rv 10004:10005 "$OUTPUT_DIR"

