#!/bin/bash

# Function to check if the script is running as root
check_root() {
  if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root."
    exit 1
  fi
}

# Function to detect the operating system
detect_os() {
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
  else
    echo "Could not determine the operating system."
    exit 1
  fi
}

# Function to find an available UID under 1000
find_available_uid() {
  for uid in $(seq 101 999); do
    if ! getent passwd "$uid" > /dev/null; then
      echo "$uid"
      return
    fi
  done
  echo "No available UID found under 1000."
  exit 1
}

# Function to create the ansible user on Ubuntu
create_ubuntu_user() {
  local uid
  uid=$(find_available_uid)
  useradd -r -u "$uid" -m -d /var/lib/ansible -s /bin/bash ansible
  usermod -aG sudo ansible
  echo "ansible ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/ansible > /dev/null
  sudo chmod 0440 /etc/sudoers.d/ansible
  sudo chown root:root /etc/sudoers.d/ansible
}

# Function to create the ansible user on Amazon Linux
create_amazon_linux_user() {
  local uid
  uid=$(find_available_uid)
  sudo sed -i '/^\s*ssh_pwauth:.*$/d' /etc/cloud/cloud.cfg
  adduser -r -u "$uid" -m -d /var/lib/ansible -s /bin/bash ansible
  usermod -aG wheel ansible
  echo "ansible ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/ansible > /dev/null
  sudo chmod 0440 /etc/sudoers.d/ansible
  sudo chown root:root /etc/sudoers.d/ansible
}

# Function to set the ansible user password
set_password() {
  passwd ansible
}

# Check if the script is running as root
check_root

# Detect the operating system
detect_os

# Create the ansible user based on the operating system
case $OS in
  "Ubuntu")
    create_ubuntu_user
    ;;
  "Amazon Linux")
    create_amazon_linux_user
    ;;
  *)
    echo "Unsupported operating system: $OS"
    exit 1
    ;;
esac

# Set the ansible user password
set_password

echo "Ansible user has been successfully created, added to the sudoers group, and configured for password-free sudo access."
