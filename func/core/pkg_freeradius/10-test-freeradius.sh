#!/bin/bash
r_log "freeradius" "Test basic freeradius functionality"

r_log "freeradius" "Configure freeradius"
cp /etc/raddb/users /etc/raddb/users.backup
cat >> /etc/raddb/users << EOF
rocky  Cleartext-Password := "rocky"
       Service-Type = Framed-User
EOF

r_log "freeradius" "Testing..."
echo "User-Name=rocky,User-Password=rocky " | radclient -x localhost:1812 auth testing123 | grep -q 'Access-Accept'
r_checkExitStatus $?

cp /etc/raddb/users.backup /etc/raddb/users
rm -rf /etc/raddb/users.backup
service radiusd stop
