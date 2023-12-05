#!/bin/bash
r_log "httpd" "Test basic php"

echo "<?php echo phpinfo(); ?>" > /var/www/html/test.php
# This isn't normally needed, it should just work
restorecon -R /var/www/html
curl -s http://localhost/test.php | grep -q 'PHP Version' > /dev/null 2>&1

r_checkExitStatus $?
