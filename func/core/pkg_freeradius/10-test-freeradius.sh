#!/bin/bash
function cleanup() {
  cp /etc/raddb/users.backup /etc/raddb/users
  rm -rf /etc/raddb/users.backup
  systemctl stop radiusd.service
}

r_log "freeradius" "Test basic freeradius functionality"
r_log "freeradius" "Configure freeradius"
trap cleanup EXIT

cp /etc/raddb/users /etc/raddb/users.backup
cat >> /etc/raddb/users << EOF
rocky  Cleartext-Password := "rocky"
       Service-Type = Framed-User
EOF

r_log "freeradius" "Testing..."
systemctl start radiusd.service
sleep 1
echo "User-Name=rocky,User-Password=rocky " | radclient -x localhost:1812 auth testing123 | grep -q 'Access-Accept'
r_checkExitStatus $?
