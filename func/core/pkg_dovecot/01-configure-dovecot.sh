#!/bin/bash
r_log "dovecot" "Configuring dovecot"

cat > /etc/dovecot/conf.d/11-rocky.conf << EOF
mail_location = mbox:~/mail:INBOX=/var/mail/%u
mail_privileged_group = mail
EOF

m_serviceCycler dovecot restart
