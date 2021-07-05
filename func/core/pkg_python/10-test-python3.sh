#!/bin/bash
r_log "python" "Test python basic printing"

cat > /var/tmp/test.py << EOF
print("Hello!")
EOF
/usr/bin/python3 /var/tmp/test.py | grep -q "Hello!"
r_checkExitStatus $?
