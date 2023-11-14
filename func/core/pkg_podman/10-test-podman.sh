#!/bin/bash

r_log "podman" "Testing podman"

test_to_run=(
  "podman version"
  "podman info"
  "podman run --rm quay.io/rockylinux/rockylinux:${RL_VER}"
  "podman system service -t 1"
  "touch ${HOME}/test.txt && \
   podman run --rm --privileged -v ${HOME}/test.txt:/test.txt quay.io/rockylinux/rockylinux:${RL_VER} bash -c 'echo HELLO > /test.txt' && \
   grep -qe 'HELLO' ${HOME}/test.txt && \
   rm -f ${HOME}/test.txt"
  "printf \"FROM quay.io/rockylinux/rockylinux:${RL_VER}\nCMD echo 'HELLO'\n\" > ${HOME}/Containerfile && \
   podman build -t test:latest -f ${HOME}/Containerfile && \
   podman image rm localhost/test:latest && \
   rm -rf ${HOME}/Containerfile"
)

tmpoutput="$(mktemp)"
trap 'rm -f ${tmpoutput}' EXIT

for command in "${test_to_run[@]}"; do
  r_log "podman" "Running $0: ${command}"
  if ! eval "${command}" > "${tmpoutput}" 2>&1; then
    r_log "podman" "${command} has failed."
    cat "${tmpoutput}"
    exit 1
  else
    r_checkExitStatus 0
  fi
done
