#!/bin/bash
r_log "file" "Check mimetype of bash"

# Add additional versions here when ready
case "$RL_VER" in
  8)
    MIME="application/x-sharedlib"
    ;;
  *)
    # This is from fedora, 9 may or may not be this
    MIME="application/x-pie-executable"
    ;;
esac

file -i /bin/bash | grep -q "${MIME}"
r_checkExitStatus $?
