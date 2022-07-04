#!/bin/bash
# This is a template that is used to build ISO's for Rocky Linux. Only under
# extreme circumstances should you be filling this out and running manually.

set -o pipefail

# Vars
MOCK_CFG="/var/tmp/lorax-{{ major }}.cfg"
MOCK_ROOT="/var/lib/mock/{{ shortname|lower }}-{{ major }}-{{ arch }}"
MOCK_RESL="${MOCK_ROOT}/result"
MOCK_CHRO="${MOCK_ROOT}/root"
MOCK_LOG="${MOCK_RESL}/mock-output.log"
LORAX_SCR="/var/tmp/buildImage.sh"
LORAX_TAR="lorax-{{ revision }}-{{ arch }}.tar.gz"
ISOLATION="{{ isolation }}"
BUILDDIR="{{ builddir }}"

# Init the container
mock \
  -r "${MOCK_CFG}" \
  --isolation="${ISOLATION}" \
  --enable-network \
  --init

init_ret_val=$?
if [ $init_ret_val -ne 0 ]; then
  echo "!! MOCK INIT FAILED !!"
  exit 1
fi

mkdir -p "${MOCK_RESL}"
cp "${LORAX_SCR}" "${MOCK_CHRO}${LORAX_SCR}"

mock \
  -r "${MOCK_CFG}" \
  --shell \
  --isolation="${ISOLATION}" \
  --enable-network -- /bin/bash "${LORAX_SCR}" | tee -a "${MOCK_LOG}"

mock_ret_val=$?
if [ $mock_ret_val -eq 0 ]; then
  # Copy resulting data to /var/lib/mock/{{ shortname|lower }}-{{ major }}-{{ arch }}/result
  mkdir -p "${MOCK_RESL}"
  cp "${MOCK_CHRO}${BUILDDIR}/${LORAX_TAR}" "${MOCK_RESL}"
else
  echo "!! LORAX RUN FAILED !!"
  exit 1
fi

# Clean up?
