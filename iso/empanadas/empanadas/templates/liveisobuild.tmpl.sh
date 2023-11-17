#!/bin/bash
# This is a template that is used to build extra ISO's for Rocky Linux. Only
# under extreme circumstances should you be filling this out and running
# manually.

set -o pipefail

# Vars
MOCK_CFG="/var/tmp/live-{{ releasever }}.cfg"
MOCK_ROOT="/var/lib/mock/{{ shortname|lower }}-{{ releasever }}-{{ arch }}"
MOCK_RESL="${MOCK_ROOT}/result"
MOCK_CHRO="${MOCK_ROOT}/root"
MOCK_LOG="${MOCK_RESL}/mock-output.log"
IMAGE_SCR="{{ entries_dir }}/buildLiveImage-{{ arch }}-{{ image }}.sh"
IMAGE_ISO="{{ isoname }}"
ISOLATION="{{ isolation }}"
BUILDDIR="{{ builddir }}"

#if [ -f "/usr/sbin/setenforce" ]; then
#  sudo setenforce 0
#fi

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
cp "${IMAGE_SCR}" "${MOCK_CHRO}${IMAGE_SCR}"

mock \
  -r "${MOCK_CFG}" \
  --shell \
  --isolation="${ISOLATION}" \
  --enable-network -- /bin/bash "${IMAGE_SCR}" | tee -a "${MOCK_LOG}"

mock_ret_val=$?
if [ $mock_ret_val -eq 0 ]; then
  # Copy resulting data to /var/lib/mock/{{ shortname|lower }}-{{ releasever }}-{{ arch }}/result
  mkdir -p "${MOCK_RESL}"
  cp "${MOCK_CHRO}${BUILDDIR}/lmc/${IMAGE_ISO}" "${MOCK_RESL}"
else
  echo "!! EXTRA ISO RUN FAILED !!"
  exit 1
fi

# Clean up?
#if [ -f "/usr/sbin/setenforce" ]; then
#  sudo setenforce 1
#fi
