#!/bin/bash
r_log "postfix" "Install postfix (requires stop of other pieces)"
# This is OK if it fails - This is also not logged except in stderr
m_serviceCycler sendmail stop
p_installPackageNormal postfix nc dovecot openssl
m_serviceCycler postfix enable
m_serviceCycler postfix start
