#!/bin/bash
function cleanup() {
  rm /etc/httpd/conf.d/vhost.conf
  sed -i '/127.0.0.1 coretest/d' /etc/hosts
  m_serviceCycler httpd reload
}

r_log "httpd" "Test basic vhost functionality"
trap cleanup EXIT

echo "127.0.0.1 coretest" >> /etc/hosts
cat > /etc/httpd/conf.d/vhost.conf << EOF
## Core vhost test
NameVirtualHost *:80
<VirtualHost *:80>
  ServerName coretest
  ServerAdmin root@localhost
  DocumentRoot /var/www/vhost/coretest
</VirtualHost>
EOF

mkdir -p /var/www/vhost/coretest
echo "core vhost test page" > /var/www/vhost/coretest/index.html
m_serviceCycler httpd cycle

curl -s http://coretest/ | grep -q 'core vhost test page' > /dev/null 2>&1

r_checkExitStatus $?
