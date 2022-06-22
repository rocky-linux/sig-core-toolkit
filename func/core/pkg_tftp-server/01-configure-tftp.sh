#!/bin/bash
r_log "tftp" "Configure tftp"

if [ "$RL_VER" -eq 8 ]; then
  cat <<EOF > /etc/xinetd.d/tftp
service tftp
{
    socket_type   = dgram
    protocol      = udp
    wait          = yes
    user          = root
    server        = /usr/sbin/in.tftpd
    server_args   = -s /var/lib/tftpboot
    disable       = no
    per_source    = 11
    cps           = 100 2
    flags         = IPv4
}
EOF

fi

m_serviceCycler tftp.socket start
