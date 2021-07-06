#!/bin/bash
r_log "network" "Test bridging functionality (non-network manager)"

bridge=dummybr0
# shellcheck disable=SC1091,1090
. "$(dirname "$0")"/imports.sh

r_log "network" "Add a dummy bridge $bridge"
ret_val=$(iproute_add_bridge $bridge)
r_checkExitStatus "$ret_val"

r_log "network" "Clean up/Remove bridge"
ret_val=$(iproute_del_bridge $bridge)
r_checkExitStatus "$ret_val"
