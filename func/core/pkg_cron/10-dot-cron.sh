#!/bin/bash
r_log "cron" "Testing hourly cron jobs"

cat > /etc/cron.hourly/rocky.sh <<EOF
#!/bin/bash
echo "obsidian"
EOF

chmod +x /etc/cron.hourly/rocky.sh

run-parts /etc/cron.hourly | grep -q "obsidian"
r_checkExitStatus $?

r_log "cron" "Testing daily cron jobs"

cat > /etc/cron.daily/rocky.sh <<EOF
#!/bin/bash
echo "obsidian"
EOF

chmod +x /etc/cron.daily/rocky.sh

run-parts /etc/cron.daily | grep -q "obsidian"
r_checkExitStatus $?

r_log "cron" "Testing weekly cron jobs"

cat > /etc/cron.weekly/rocky.sh <<EOF
#!/bin/bash
echo "obsidian"
EOF

chmod +x /etc/cron.weekly/rocky.sh

run-parts /etc/cron.weekly | grep -q "obsidian"
r_checkExitStatus $?

/bin/rm /etc/cron.{weekly,daily,hourly}/rocky.sh
