#!/bin/bash
r_log_"lamp" "Verify LAMP can potentially work"

PHP_CHECK=/tmp/php.check

# This may not change for EL9
if [ "$RL_VER" -ge 8 ]; then
  SQL=mariadb
else
  SQL=mysqld
fi

# for Justin Case
rm -f "${PHP_CHECK}"

r_log "lamp" "Starting up httpd and MySQL/mariadb"

m_serviceCycler httpd restart
m_serviceCycler $SQL restart

r_log "lamp" "We did this before, but double check PHP works"
echo "<?php echo phpinfo(); ?>" > $PHP_CHECK

/bin/php $PHP_CHECK &> /dev/null
r_checkExitStatus $?
