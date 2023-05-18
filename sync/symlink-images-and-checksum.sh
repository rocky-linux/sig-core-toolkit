#!/bin/bash
# shellcheck disable=SC2046,1091,1090
source $(dirname "$0")/common
for ARCH in "${ARCHES[@]}"; do
  pushd "${STAGING_ROOT}/${CATEGORY_STUB}/${REV}/isos/${ARCH}" || { echo "Could not change directory"; break; }

  if [ -f "CHECKSUM" ]; then
    rm CHECKSUM
  fi

  for ISO in *.iso; do
    ln -s "${ISO}" "${ISO//.[0-9]/-latest}"
  done

  # shellcheck disable=SC2086
  for file in *.iso; do
    printf "# %s: %s bytes\n%s\n" \
      "${file}" \
      "$(stat -c %s ${file} -L)" \
      "$(sha256sum --tag ${file})" \
    | sudo tee -a CHECKSUM;
  done

  popd || { echo "Could not change directory"; break; }
done
