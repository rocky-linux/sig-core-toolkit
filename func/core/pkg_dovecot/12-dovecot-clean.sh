#!/bin/bash
rm -f /etc/dovecot/conf.d/11-rocky.conf
m_serviceCycler dovecot restart
