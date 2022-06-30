#!/bin/bash
if m_getArch aarch64 | grep -qE 'aarch64'; then
  r_log "ipa" "Skipping for aarch64"
  exit 0
fi

r_log "ipa" "Removing the httpd package if present"
if rpm -q httpd &> /dev/null; then
  p_removePackage httpd
  rm -rf /etc/httpd
fi

r_log "ipa" "Removing the bind package if present"
if rpm -q httpd &> /dev/null; then
  p_removePackage bind
  rm -rf /etc/named /var/named
fi

mkdir /root/ipa-backup
r_log "ipa" "Backup dnf history"
dnf history list | awk 'NR == 4 {print $1}' > /root/ipa-backup/dnf-history.ipa

r_log "ipa" "Backup necessary files in /etc"
r_log "ipa" "/etc/resolv.conf"
cp /etc/resolv.conf /root/ipa-backup
r_log "ipa" "/etc/nsswitch.conf"
cp /etc/nsswitch.conf /root/ipa-backup
r_log "ipa" "/etc/hosts"
cp /etc/hosts /root/ipa-backup
r_log "ipa" "/etc/hostname"
cp /etc/hostname /root/ipa-backup
# For Justin Case
hostname > /root/ipa-backup/hostname-command

# Not really necessary, an NTP server shouldn't be default anymore
r_log "ipa" "/etc/chrony.conf"
cp /etc/chrony.conf /root/ipa-backup

r_log "ipa" "/etc/ssh/ssh_config"
cp /etc/ssh/ssh_config /root/ipa-backup

r_log "ipa" "Removing hostname from /etc/hosts"
sed -i "s|127.0.0.1 $(hostname)||" /etc/hosts

r_log "ipa" "Removing tomcat if installed"
p_removePackage ipa-server tomcat
rm -rf /var/lib/pki/pki-tomcat/ \
  /etc/sysconfig/pki-tomcat \
  /var/log/pki/pki-tomcat \
  /etc/pki/pki-tomcat \
  /etc/sysconfig/pki/tomcat/pki-tomcat
