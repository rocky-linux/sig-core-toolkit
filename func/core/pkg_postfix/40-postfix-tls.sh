#!/bin/bash
r_log "postfix" "Test postfix with TLS"
DROPDIR=/var/tmp/postfix

function cleanup() {
  mv /etc/postfix/main.cf.backup /etc/postfix/main.cf
  mv /etc/dovecot/dovecot.conf.backup /etc/dovecot/dovecot.conf
  rm /etc/pki/tls/certs/mail.crt
  rm /etc/pki/tls/private/mail.key
  rm -rf $DROPDIR/mail.*
  rm -rf /var/tmp/postfix
}

trap cleanup EXIT

cp -a /etc/postfix/main.cf /etc/postfix/main.cf.backup
cp -a /etc/dovecot/dovecot.conf /etc/dovecot/dovecot.conf.backup

cat ./common/files/postfix-test-tls >> /etc/postfix/main.cf
cat ./common/files/dovecot-test-sasl >> /etc/dovecot/dovecot.conf

mkdir $DROPDIR

r_log "postfix" "Creating mail certificate and keys"

openssl genrsa -passout pass:obsidian -des3 -out $DROPDIR/mail.key.secure 4096 > /dev/null 2>&1
ret_val=$?
if [ $ret_val -ne 0 ]; then
  r_log "postfix" "Could not create private key."
  r_checkExitStatus 1
fi

openssl rsa -passin pass:rocky -in "$DROPDIR/mail.key.secure" -out "$DROPDIR/mail.key" > /dev/null 2>&1
ret_val=$?
if [ $ret_val -ne 0 ]; then
  r_log "postfix" "Could not create mail private key from secure key"
  r_checkExitStatus 1
fi

if [ ! -f ./common/files/openssl-answers ]; then
  r_log "postfix" "We do not have our openssl answers file"
  r_checkExitStatus 1
fi

openssl req -batch -config ./common/files/openssl-answers -new -key "$DROPDIR/mail.key" -out "$DROPDIR/mail.csr" > /dev/null 2>&1
ret_val=$?
if [ $ret_val -ne 0 ]; then
  r_log "postfix" "Could not create mail csr"
  r_checkExitStatus 1
fi

openssl x509 -req -days 365 -in "$DROPDIR/mail.csr" -signkey "$DROPDIR/mail.key" -out "$DROPDIR/mail.crt" > /dev/null 2>&1
ret_val=$?
if [ $ret_val -ne 0 ]; then
  r_log "postfix" "Could not create self-signed certificate"
  r_checkExitStatus 1
fi

cp "$DROPDIR/mail.key" /etc/pki/tls/private/
cp "$DROPDIR/mail.crt" /etc/pki/tls/certs/

chmod 400 /etc/pki/tls/private/mail.key
chown postfix:postfix /etc/pki/tls/private/mail.key /etc/pki/tls/certs/mail.crt

m_serviceCycler postfix restart
m_serviceCycler dovecot restart

r_log "postfix" "Testing that postfix offers STARTTLS"

echo "ehlo test" | nc -w 3 127.0.0.1 25 | grep -q "STARTTLS"
ret_val=$?

r_checkExitStatus $ret_val
