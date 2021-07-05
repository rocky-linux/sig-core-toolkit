#!/bin/bash
r_log "postfix" "Test postfix sasl support"

cp -a /etc/postfix/main.cf /etc/postfix/main.cf.backup
cp -a /etc/dovecot/dovecot.conf /etc/dovecot/dovecot.conf.backup

cat ./common/files/postfix-test-sasl >> /etc/postfix/main.cf
cat ./common/files/dovecot-test-sasl >> /etc/dovecot/dovecot.conf

m_serviceCycler dovecot restart
m_serviceCycler postfix restart

r_log "postfix" "Testing that postfix accepts connections and plain auth"
echo "ehlo test" | nc -w 3 127.0.0.1 25 | grep -q 'AUTH PLAIN'
ret_val=$?

mv /etc/dovecot/dovecot.conf.backup /etc/dovecot/dovecot.conf
mv /etc/postfix/main.cf.backup /etc/postfix/main.cf

r_checkExitStatus $ret_val

cp -a /etc/postfix/main.cf.backup /etc/postfix/main.cf
cp -a /etc/dovecot/dovecot.conf.backup /etc/dovecot/dovecot.conf
