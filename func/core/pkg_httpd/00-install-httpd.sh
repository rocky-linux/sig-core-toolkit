#!/bin/bash
r_log "httpd" "Install httpd"

p_installPackageNormal curl httpd mod_ssl php-mysqlnd php
m_serviceCycler httpd cycle
