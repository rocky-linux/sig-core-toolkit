#!/bin/bash
r_log "httpd" "Test basic authentication functionality"

cat > /etc/httpd/conf.d/test-basic-auth.conf <<EOF
## Core basic auth test
Alias /basic_auth /var/www/html/basic_auth
<Directory "/var/www/html/basic_auth">
  AuthType Basic
  AuthName "Test"
  AuthUserFile /etc/httpd/htpasswd
  require user tester
</Directory>
EOF

htpasswd -c -b /etc/httpd/htpasswd tester tester
mkdir -p /var/www/html/basic_auth
echo "Basic Auth Test" > /var/www/html/basic_auth/index.html
m_serviceCycler httpd cycle
curl -s -u tester:tester http://localhost/basic_auth/ | grep -q 'Basic Auth Test' > /dev/null 2>&1
r_checkExitStatus $?

rm /etc/httpd/conf.d/test-basic-auth.conf
m_serviceCycler httpd reload
