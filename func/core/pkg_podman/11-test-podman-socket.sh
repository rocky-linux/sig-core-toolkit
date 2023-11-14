#!/bin/bash

r_log "podman" "Testing podman sockets"

useradd podman-remote
loginctl enable-linger podman-remote
tmpoutput="$(mktemp)"

trap 'loginctl terminate-user podman-remote && loginctl disable-linger podman-remote && sleep 1 && userdel -r podman-remote && rm -f ${tmpoutput}' EXIT

sleep 3

su -l podman-remote > "${tmpoutput}" 2>&1 <<EOF
set -e
export XDG_RUNTIME_DIR=/run/user/\$(id -u)
systemctl --user enable --now podman.socket
podman --url unix://run/user/\$(id -u)/podman/podman.sock run --name port-mapping-test -d -p 8080:80 docker.io/nginx
pid=\$(systemctl --user show --property MainPID --value podman.service)
while [ "\${pid}" -ne 0 ] && [ -d /proc/\${pid} ]; do sleep 1; echo "Waiting for podman to exit"; done
podman --url unix://run/user/\$(id -u)/podman/podman.sock ps | grep -q -e port-mapping-test
podman --url unix://run/user/\$(id -u)/podman/podman.sock container rm -f port-mapping-test
systemctl --user disable --now podman.socket
EOF

ret_val=$?

if [ "$ret_val" -ne 0 ]; then
  cat "${tmpoutput}"
  r_checkExitStatus 1
fi
r_checkExitStatus 0
