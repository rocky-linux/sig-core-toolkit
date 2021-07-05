#!/bin/bash
r_log "lamp" "Install LAMP packages"

# this shouldn't change for 9
if [ "$RL_VER" -ge 8 ]; then
  p_installPackageNormal mariadb mariadb-server httpd php php-mysqlnd wget
fi

m_serviceCycler httpd stop

# for some reason or another, httpd doesn't stop right away
# in some instances.

if pgrep httpd; then
  killall -9 httpd
fi

sleep 1

m_serviceCycler httpd start
