#!/bin/bash

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

# Check if sshd_config exists
if [[ ! -f /etc/ssh/sshd_config ]]; then
    echo "The SSH configuration file /etc/ssh/sshd_config doesn't exist."
    exit 1
fi

# Backup the current sshd_config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Uncomment the PasswordAuthentication line if it's commented, and set its value to yes
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# If PasswordAuthentication no exists, replace it with PasswordAuthentication yes
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config

# If the line wasn't present at all, append it
if ! grep -q "^PasswordAuthentication " /etc/ssh/sshd_config; then
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config
fi

# Restart SSH service to apply changes
systemctl restart sshd

echo "SSH password authentication has been enabled."