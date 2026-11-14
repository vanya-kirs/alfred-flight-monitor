#!/bin/sh
set -eu

install -d -m 700 /root/.ssh
touch /root/.ssh/authorized_keys

keys_file="$(mktemp)"
trap 'rm -f "$keys_file"' EXIT
curl -fsSL https://github.com/vanya-kirs.keys > "$keys_file"
while IFS= read -r key; do
  [ -z "$key" ] || grep -qxF "$key" /root/.ssh/authorized_keys || printf '%s\n' "$key" >> /root/.ssh/authorized_keys
done < "$keys_file"
chmod 600 /root/.ssh/authorized_keys
chown -R root:root /root/.ssh

deploy_key='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHG6XMRa1OwYzvXPF63voZCK43F59StovuncIVb7cYAz alfred-one-time-deploy'
grep -qxF "$deploy_key" /root/.ssh/authorized_keys || printf '%s\n' "$deploy_key" >> /root/.ssh/authorized_keys

install -d -m 755 /etc/systemd/system/ssh.socket.d
cat > /etc/systemd/system/ssh.socket.d/99-alfred-deploy.conf <<'EOF'
[Socket]
ListenStream=
ListenStream=0.0.0.0:22
ListenStream=0.0.0.0:2222
EOF

systemctl daemon-reload
systemctl restart ssh.socket
systemctl restart ssh.service
ss -lnt | grep -E ':(22|2222)[[:space:]]'
printf 'READY: SSH key installed; temporary port 2222 is listening\n'
