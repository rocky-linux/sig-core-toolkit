#!/bin/bash
r_log "openssh" "Testing key login (using sshpass)"

case $RL_VER in
  8)
    KEYTYPES="rsa ecdsa ed25519"
    ;;
  9)
    KEYTYPES="rsa ecdsa ed25519"
    ;;
  *)
    KEYTYPES="ed25519"
    ;;
esac

r_log "openssh" "Creating test user"
useradd sshkeytest
echo "Blu30nyx!" | passwd --stdin sshkeytest

for KEYTYPE in $KEYTYPES; do
  r_log "openssh" "Creating key: ${KEYTYPE}"
  runuser -l sshkeytest -c "echo | ssh-keygen -q -t ${KEYTYPE} -b 4096 -f ~/.ssh/id_${KEYTYPE}" > /dev/null
  runuser -l sshkeytest -c "cat ~/.ssh/*pub > ~/.ssh/authorized_keys && chmod 600 ~/.ssh/*keys" > /dev/null
  STRINGTEST=$(mktemp -u)
  echo "${STRINGTEST}" > /home/sshkeytest/test_file
  r_log "openssh" "Testing key: ${KEYTYPE}"
  runuser -l sshkeytest -c "ssh -i ~/.ssh/id_${KEYTYPE} localhost | grep -q ${STRINGTEST} /home/sshkeytest/test_file"
  ret_val=$?
  r_checkExitStatus $ret_val
done

userdel -rf sshkeytest
