#!/bin/bash
r_log "openssl" "Create openssl certificates and verify"
DROPDIR=/var/tmp/openssl
mkdir -p $DROPDIR

openssl genrsa -passout pass:obsidian -des3 -out $DROPDIR/openssl.key.secure 4096 > /dev/null 2>&1
ret_val=$?
if [ $ret_val -ne 0 ]; then
  r_log "openssl" "Failed creating private key"
  r_checkExitStatus 1
fi

openssl rsa -passin pass:obsidian -in "$DROPDIR/openssl.key.secure" -out "$DROPDIR/openssl.key" > /dev/null 2>&1
ret_val=$?
if [ $ret_val -ne 0 ]; then
  r_log "openssl" "Could not create openssl private key from secure key"
  r_checkExitStatus 1
fi

if [ ! -f ./common/files/openssl-answers ]; then
  r_log "openssl" "We do not have our openssl answers file"
  r_checkExitStatus 1
fi

openssl req -batch -config ./common/files/openssl-answers -new -key "$DROPDIR/openssl.key" -out "$DROPDIR/openssl.csr" > /dev/null 2>&1
ret_val=$?
if [ $ret_val -ne 0 ]; then
  r_log "openssl" "Could not create openssl csr"
  r_checkExitStatus 1
fi

openssl x509 -req -days 365 -in "$DROPDIR/openssl.csr" -signkey "$DROPDIR/openssl.key" -out "$DROPDIR/openssl.crt" > /dev/null 2>&1
ret_val=$?
if [ $ret_val -ne 0 ]; then
  r_log "openssl" "Could not create self-signed certificate"
  r_checkExitStatus 1
fi

SSLVAR=$(openssl version -d)
SSLREGEX='OPENSSLDIR\:\ \"(.*)\"'
if [[ "$SSLVAR" =~ $SSLREGEX ]]; then
  SSLPATH=${BASH_REMATCH[1]}
else
  r_log "openssl" "Could not find the openssl config directory"
  r_checkExitStatus 1
fi

cp "$DROPDIR/openssl.crt" "$SSLPATH/certs/"
# shellcheck disable=SC2086
HASH="$(openssl x509 -noout -hash -in $SSLPATH/certs/openssl.crt)"
ret_val=$?
if [ $ret_val -ne 0 ]; then
  r_log "openssl" "Could not create hash"
fi

ln -s "$SSLPATH/certs/openssl.crt" "$SSLPATH/certs/${HASH}.0"

openssl verify $DROPDIR/openssl.crt | grep -cq OK
ret_val=$?
if [ $ret_val -ne 0 ]; then
  r_log "openssl" "Self signed certificate verification failed"
  r_checkExitStatus 1
fi

r_checkExitStatus 0

rm -rf $DROPDIR/certs "$SSLPATH/certs/${HASH}.0" "$SSLPATH/certs/openssl.crt"
