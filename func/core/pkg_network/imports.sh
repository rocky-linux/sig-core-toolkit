#!/bin/bash
function iproute_add_bridge() {
  BRIDGE=$1
  PRESENCE=$(grep "$BRIDGE" /proc/net/dev)
  if ! [ "${PRESENCE}" ]; then
    ip link add name "$BRIDGE" type bridge
    PRESENCE=$(grep "$BRIDGE" /proc/net/dev)
    if [ "${PRESENCE}" ]; then
      ret_val=0
    else
      echo "$BRIDGE was not created"
      ret_val=1
    fi
  else
    ret_val=0
  fi
  echo "$ret_val"
}

function iproute_del_bridge() {
  BRIDGE=$1
  PRESENCE=$(grep "$BRIDGE" /proc/net/dev)
  if ! [ "${PRESENCE}" ]; then
    echo "$BRIDGE doesn't exist"
    ret_val=1
  else
    ip link del "$BRIDGE" type bridge
    PRESENCE=$(grep "$BRIDGE" /proc/net/dev)
    if [ "${PRESENCE}" ]; then
      echo "Bridge was not be deleted"
      ret_val=1
    else
      ret_val=0
    fi
  fi
  echo "$ret_val"
}
