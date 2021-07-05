#!/bin/bash
r_log "postfix" "Install postfix (requires stop of other pieces)"
m_serviceCycler sendmail stop
p_installPackageNormal postfix nc dovecot openssl
m_serviceCycler postfix enable
m_serviceCycler postfix start
