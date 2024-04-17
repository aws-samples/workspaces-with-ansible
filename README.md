# What is this code repository?

This code repository contains code to use Ansible® with Amazon WorkSpaces. Specifically, it includes an Ansible dynamic inventory provider, and some starter Ansible playbooks.

## What is Ansible? 

Ansible allows you to automate the management of remote systems and control their desired state. You can use Ansible to perform tasks across your fleet of WorkSpaces, such as:

*	Listing installed programs
*	Installing and upgrading programs
*	Performing system patching
*	Verifying patching compliance.

For more information, see these documentation links from Ansible:

* [Getting started with Ansible.](https://docs.ansible.com/ansible/latest/getting_started/index.html)
* [Ansible homepage.](https://www.ansible.com/)

## What is an Ansible inventory provider?

Ansible needs an inventory file in order to run commands against specific computers. An inventory file could be a static file with hardcoded IP addresses, computer names, or a CIDR IP range. There are notable pain points with both approaches.

* A static text file with hardcoded IP addresses/computer names requires manual upkeep.
* A static text file with IP ranges will take a very long time to execute, as the Ansible control server will iterate over IP addresses which don't actually have a corresponding WorkSpace, yet are within the range.
* Both methods will cause delays on `AUTO_STOP` WorkSpaces which are offline, as Ansible tries to send commands to a non-responsive server.
* In the case of Windows, Kerberos authentication won't be possible with IP addresses. The computer name needs to be used for WinRM to function with Kerberos.

Ansible also has the concept of **dynamic inventory providers**, which are much more flexible. Ansible ships these for some existing AWS services (such as EC2 and RDS) but not for WorkSpaces. The module in this repository does the following things:

* uses the public [describe_workspaces](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/workspaces/client/describe_workspaces.html) API call to generate a list of WorkSpaces.
* filters that list, so that the only WorkSpaces it adds to inventory are in the `AVAILABLE` state.
* filters the list by operating system, using the `OperatingSystemName` value. This lets you filter by OS version as well, such as Windows Server 2016 vs Windows Server 2019. 
  * Additionally, Windows WorkSpaces will have their IP addresses replaced with the computer hostname (also from the API), so that Kerberos functions for authentication. WinRM will also be used as the connection method, rather than SSH.
  * Windows WorkSpaces will use hostnames because the default behavior for Windows and Kerberos [is to reject connection requests made directly to IP addresses.](https://learn.microsoft.com/en-us/windows-server/security/kerberos/configuring-kerberos-over-ip)

When using the Ansible playbooks in this repo (or that you write), you will use the dynamic inventory provider rather than building a flat file inventory. The inventory provider will re-run on each use of the commands, to ensure that inventory is always up to date.

The dynamic inventory provider uses `boto3` pagination and exponential backoff and retry as best practices for interacting with the API. 

For more information on Ansible's inventory system, see these documentation links:

* [Ansible inventory.](https://docs.ansible.com/ansible/latest/inventory_guide/index.html)
* [Ansible dynamic inventory.](https://docs.ansible.com/ansible/latest/inventory_guide/intro_dynamic_inventory.html)

### A note about large WorkSpaces fleets

If you have a large fleet of WorkSpaces (over a thousand), filtering by Directory ID will make the API calls more efficient.


# How do I get started with this?

These steps assume the use of an Ubuntu 22.04 control server for Ansible. Ansible control servers cannot be installed on Windows.

After creating your Ubuntu 22.04 instance, you can connect to it with either SSH or with AWS Systems Manager Session Manager.

While connected to your Ubuntu instance, run the following commands. Be sure to run the `pip3` command as written, not with `sudo` in front of it. 

```bash
sudo add-apt-repository --yes ppa:ansible/ansible
sudo apt update
sudo apt-get install python3-pip ansible jq realmd krb5-user -y
pip3 install boto3
```

After the installation steps are complete, clone this repository to download the inventory provider and example playbooks with the following commands. The first command ensures that your current working directory is your home folder before the repository is cloned.

```bash
cd ~
git clone https://github.com/aws-samples/workspaces-with-ansible
```

You will need to mark the inventory provider as executable:

`chmod +x ~/workspaces-with-ansible/workspaces_inventory_provider.py` 

## Running the inventory provider

Before running any commands with Ansible, you will need to specify your AWS region as an environment variable. Optionally, you can specify your AWS Directory ID as an environment variable. This is not required, but can frequently be helpful, both for applying commands with a more narrow focus as well as being more efficient with API calls.

```bash
export AWS_REGION=us-west-2
export DIRECTORY_ID=d-xxxxxxxxx
```

To remove the environment variables, you can use `unset`, such as:

```bash
unset AWS_REGION
unset DIRECTORY_ID
```

You can test run the inventory provider in one of two ways: 

* Run the inventory provider Python script by itself.
  * When you are running the script directly, `--region`, `--workspace-ids`, and `--directory-id` can be used as CLI arguments for the script. The `--workspace-ids` argument accepts one or more WorkSpace IDs, separated by spaces.
* Run the `ansible-inventory` inventory command. 
  * Note that while the Python script accepts the AWS region as an argument, `ansible-inventory` does not. Make sure to create the `AWS_REGION` environment variable, and, if desired, the `DIRECTORY_ID` variable.

Here is example output for both:

```bash
ssm-user@ip-10-0-2-235:~$ ansible-inventory -i ~/workspaces-with-ansible/workspaces_inventory_provider.py --graph
@all:
  |--@ungrouped:
  |--@ubuntu_22_04_workspaces:
  |  |--172.16.0.250
  |  |--10.0.0.241
  |  |--172.16.1.136
  |  |--10.0.0.114
  |  |--10.0.2.193
  |  |--10.0.0.226
  |  |--10.0.2.239
  |  |--10.0.2.223
  |  |--10.0.2.44
  |  |--10.0.2.33
  |--@windows_11_workspaces:
  |  |--10.0.2.29
  |--@amazon_linux_2_workspaces:
  |  |--10.0.2.93
  |  |--172.16.1.204
  |  |--10.0.2.206
  |  |--172.16.0.34
  |--@windows_server_2019_workspaces:
  |  |--10.0.0.192
  |  |--172.16.0.232
  |  |--172.16.1.193
  |  |--10.0.0.144
  |  |--10.0.2.146
  |  |--10.0.0.45
  |  |--10.0.2.24
  |  |--10.0.2.88
  |--@windows_server_2022_workspaces:
  |  |--10.0.2.243
  |--@windows_10_workspaces:
  |  |--10.0.0.12
ssm-user@ip-10-0-2-235:~$
```

Compare with the output of the inventory python script directly. Note that the Windows WorkSpaces have their IP addresses set with an override to use their hostname instead. This is because the default behavior for Windows and Kerberos [is to reject connection requests made directly to IP addresses](https://learn.microsoft.com/en-us/windows-server/security/kerberos/configuring-kerberos-over-ip).

```bash
ssm-user@ip-10-0-2-235:~$ ~/workspaces-with-ansible/workspaces_inventory_provider.py --list
{
    "_meta": {
        "hostvars": {
            "172.16.0.250": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "10.0.2.29": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": "kerberos",
                "ansible_winrm_port": "5985",
                "ansible_winrm_kerberos_hostname_override": "WORKSPA-198S9V4"
            },
            "10.0.2.93": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "10.0.0.241": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "172.16.1.136": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "10.0.0.192": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": "kerberos",
                "ansible_winrm_port": "5985",
                "ansible_winrm_kerberos_hostname_override": "WSAMZN-LIIKMS6A"
            },
            "10.0.0.114": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "172.16.0.232": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": "kerberos",
                "ansible_winrm_port": "5985",
                "ansible_winrm_kerberos_hostname_override": "WSAMZN-FT7H11RH"
            },
            "10.0.2.193": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "10.0.0.226": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "172.16.1.204": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "10.0.2.239": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "172.16.1.193": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": "kerberos",
                "ansible_winrm_port": "5985",
                "ansible_winrm_kerberos_hostname_override": "WSAMZN-SE50GKE1"
            },
            "10.0.2.223": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "10.0.0.144": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": "kerberos",
                "ansible_winrm_port": "5985",
                "ansible_winrm_kerberos_hostname_override": "WSAMZN-6M9NNE59"
            },
            "10.0.2.44": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "10.0.2.206": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "10.0.2.146": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": "kerberos",
                "ansible_winrm_port": "5985",
                "ansible_winrm_kerberos_hostname_override": "WSAMZN-J5I0628H"
            },
            "10.0.2.243": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": "kerberos",
                "ansible_winrm_port": "5985",
                "ansible_winrm_kerberos_hostname_override": "WSAMZN-PPNDUT7C"
            },
            "10.0.0.12": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": "kerberos",
                "ansible_winrm_port": "5985",
                "ansible_winrm_kerberos_hostname_override": "DESKTOP-PR6MLUL"
            },
            "10.0.2.33": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            },
            "10.0.0.45": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": "kerberos",
                "ansible_winrm_port": "5985",
                "ansible_winrm_kerberos_hostname_override": "WSAMZN-35T06K5D"
            },
            "10.0.2.24": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": "kerberos",
                "ansible_winrm_port": "5985",
                "ansible_winrm_kerberos_hostname_override": "WSAMZN-FSVJTD4N"
            },
            "10.0.2.88": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": "kerberos",
                "ansible_winrm_port": "5985",
                "ansible_winrm_kerberos_hostname_override": "WSAMZN-64309610"
            },
            "172.16.0.34": {
                "ansible_connection": "ssh",
                "ansible_user": "ansible"
            }
        }
    },
    "ubuntu_22_04_workspaces": {
        "hosts": [
            "172.16.0.250",
            "10.0.0.241",
            "172.16.1.136",
            "10.0.0.114",
            "10.0.2.193",
            "10.0.0.226",
            "10.0.2.239",
            "10.0.2.223",
            "10.0.2.44",
            "10.0.2.33"
        ],
        "vars": {}
    },
    "windows_11_workspaces": {
        "hosts": [
            "10.0.2.29"
        ],
        "vars": {}
    },
    "amazon_linux_2_workspaces": {
        "hosts": [
            "10.0.2.93",
            "172.16.1.204",
            "10.0.2.206",
            "172.16.0.34"
        ],
        "vars": {}
    },
    "windows_server_2019_workspaces": {
        "hosts": [
            "10.0.0.192",
            "172.16.0.232",
            "172.16.1.193",
            "10.0.0.144",
            "10.0.2.146",
            "10.0.0.45",
            "10.0.2.24",
            "10.0.2.88"
        ],
        "vars": {}
    },
    "windows_server_2022_workspaces": {
        "hosts": [
            "10.0.2.243"
        ],
        "vars": {}
    },
    "windows_10_workspaces": {
        "hosts": [
            "10.0.0.12"
        ],
        "vars": {}
    }
}
ssm-user@ip-10-0-2-235:~$
```

## Enabling WorkSpaces management with Ansible

In order to use Ansible with WorkSpaces, you'll need to preconfigure Security Groups to permit this for any OS. Windows will need a Group Policy to enable WinRM, and Linux will need SSH keys distributed to the WorkSpaces.

See https://catalog.us-east-1.prod.workshops.aws/workshops/54710197-fa5f-46ea-817e-9be7be8be739/en-US/workspaces-setup and its two sub-pages for example steps on how to do this. 

## Obtaining a Kerberos Token

Assuming that your Ansible server is in a VPC with a DHCP Option Set that points its DNS settings at your domain controller, you can obtain a Kerberos token this way:

```bash
kinit user@EXAMPLE.COM
```

Make sure that the domain name is in all caps. 

You can validate your Kerberos token with `klist`, e.g., 

```bash
ssm-user@ip-10-0-2-235:~$ klist
Ticket cache: FILE:/tmp/krb5cc_1001
Default principal: dan1@EXAMPLE.COM

Valid starting     Expires            Service principal
03/30/24 00:06:30  03/30/24 10:06:30  krbtgt/EXAMPLE.COM@EXAMPLE.COM
        renew until 03/31/24 00:06:24
ssm-user@ip-10-0-2-235:~$
```

# Demonstration Commands

These are demonstration commands for the included Windows and Linux playbooks.

## Windows Demonstration Commands

Now that you have your Kerberos token, you can run a command against your Windows WorkSpace. This playbook will list the installed applications on your WorkSpace along with their version number. It does this by querying the registry.

Note that if you had multiple Windows WorkSpaces, these commands would be run on all of them. Keep in mind that the dynamic inventory provider will always query the WorkSpaces API on each run, to ensure that only `AVAILABLE` WorkSpaces have commands run against them. 

### Install Notepad++

This playbook will install Notepad++ on your Windows WorkSpaces.

```bash
ansible-playbook ~/workspaces-with-ansible/install_notepadplusplus.yml -i ~/workspaces-with-ansible/workspaces_inventory.py -e "target_hosts=windows_workspaces"
```

The output will look like this:

```bash
ssm-user@ip-10-0-1-139:/var/snap/amazon-ssm-agent/7628$ ansible-playbook ~/workspaces-with-ansible/install_notepadplusplus.yml -i ~/workspaces-with-ansible/workspaces_inventory.py -e "target_hosts=windows_workspaces"

PLAY [Install Notepad++] ***************************************************************************************************************************************************************

TASK [Ensure C:\Temp exists] ***********************************************************************************************************************************************************
changed: [10.0.1.49]

TASK [Download Notepad++ Installer] ****************************************************************************************************************************************************
changed: [10.0.1.49]

TASK [Install Notepad++] ***************************************************************************************************************************************************************
changed: [10.0.1.49]

PLAY RECAP *****************************************************************************************************************************************************************************
10.0.1.49                  : ok=3    changed=3    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

### List Installed Programs

```bash
ansible-playbook ~/workspaces-with-ansible/list_installed_programs.yml -i ~/workspaces-with-ansible/workspaces_inventory.py -e "target_hosts=windows_workspaces"
```

Here is a sample output of this command, against a freshly deployed Windows WorkSpace:

```bash
ssm-user@ip-10-0-1-139:/var/snap/amazon-ssm-agent/7628$ ansible-playbook ~/workspaces-with-ansible/list_installed_programs.yml -i ~/workspaces-with-ansible/workspaces_inventory.py -e "target_hosts=windows_workspaces"

PLAY [List Installed Applications on Windows Host] *************************************************************************************************************************************

TASK [Get list of installed 64-bit applications] ***************************************************************************************************************************************
changed: [10.0.1.49]

TASK [Get list of installed 32-bit applications] ***************************************************************************************************************************************
changed: [10.0.1.49]

TASK [Combine and sort application lists] **********************************************************************************************************************************************
ok: [10.0.1.49]

TASK [Print combined list of installed applications] ***********************************************************************************************************************************
ok: [10.0.1.49] => {
    "combined_apps": [
        "",
        "                                                                                                                    ",
        "                                                                                                                       ",
        "-----------                                                        -------------- ---------                            ",
        "-----------                                                     --------------     ---------             -----------",
        "Amazon SSM Agent                                                   3.1.2144.0     Amazon Web Services                  ",
        "Amazon SSM Agent                                                3.1.2144.0         Amazon Web Services   20230412   ",
        "AWS PV Drivers                                                  8.4.3              Amazon Web Services   20230215   ",
        "AWS Tools for Windows                                              3.15.2072      Amazon Web Services Developer Rela...",
        "aws-cfn-bootstrap                                                  2.0.25         Amazon Web Services                  ",
        "aws-cfn-bootstrap                                               2.0.25             Amazon Web Services   20230511   ",
        "DisplayName                                                        DisplayVersion Publisher                            ",
        "DisplayName                                                     DisplayVersion     Publisher             InstallDate",
        "Microsoft Visual C++ 2015-2019 Redistributable (x64) - 14.29.30139 14.29.30139.0  Microsoft Corporation                ",
        "Microsoft Visual C++ 2015-2019 Redistributable (x86) - 14.25.28508 14.25.28508.3  Microsoft Corporation                ",
        "Microsoft Visual C++ 2019 X64 Additional Runtime - 14.29.30139  14.29.30139        Microsoft Corporation 20220713   ",
        "Microsoft Visual C++ 2019 X64 Minimum Runtime - 14.29.30139     14.29.30139        Microsoft Corporation 20220713   ",
        "Microsoft Visual C++ 2019 X86 Additional Runtime - 14.25.28508     14.25.28508    Microsoft Corporation                ",
        "Microsoft Visual C++ 2019 X86 Minimum Runtime - 14.25.28508        14.25.28508    Microsoft Corporation                ",
        "Mozilla Firefox (x64 en-US)                                     112.0              Mozilla                          ",
        "Mozilla Maintenance Service                                     112.0              Mozilla                          ",
        "PCoIP Standard Agent                                            20.10.8            Teradici Corporation             ",
        "Windows Driver Package - Teradici Printer  (07/13/2016 1.7.0.0) 07/13/2016 1.7.0.0 Teradici                         "
    ]
}

PLAY RECAP *****************************************************************************************************************************************************************************
10.0.1.49                  : ok=4    changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

### Check Windows Update status

Check the Windows Update status of your Windows WorkSpaces with the following command.

```bash
ansible-playbook ~/workspaces-with-ansible/check_windows_updates.yml -i ~/workspaces-with-ansible/workspaces_inventory.py -e "target_hosts=windows_workspaces"
```

Here is sample output for one Windows WorkSpace. As with the prior command, this command will run across all Windows WorkSpaces identified by the inventory provider, rather than just one host. This enables you to get a picture of your fleet at scale.

```bash
ssm-user@ip-10-0-1-139:/var/snap/amazon-ssm-agent/7628$ ansible-playbook ~/workspaces-with-ansible/check_windows_updates.yml -i ~/workspaces-with-ansible/workspaces_inventory.py -e "target_hosts=windows_workspaces"

PLAY [Windows Update State Check] ******************************************************************************************************************************************************

TASK [Check Windows Update State] ******************************************************************************************************************************************************
ok: [10.0.1.49]

TASK [Display Concise Windows Update Status] *******************************************************************************************************************************************
ok: [10.0.1.49] => (item=2023-11 Cumulative Update for Windows Server 2019 (1809) for x64-based Systems (KB5032196) (KB5032196)) => {
    "msg": "Downloaded: False, Installed: False"
}
ok: [10.0.1.49] => (item=Windows Malicious Software Removal Tool x64 - v5.119 (KB890830) (KB890830)) => {
    "msg": "Downloaded: False, Installed: False"
}
ok: [10.0.1.49] => (item=2023-11 Cumulative Update for .NET Framework 3.5, 4.7.2 and 4.8 for Windows Server 2019 for x64 (KB5032337) (KB5032337)) => {
    "msg": "Downloaded: False, Installed: False"
}

PLAY RECAP *****************************************************************************************************************************************************************************
10.0.1.49                  : ok=2    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

### Install Windows Updates

```bash
ansible-playbook ~/workspaces-with-ansible/install_windows_updates.yml -i ~/workspaces-with-ansible/workspaces_inventory.py -e "target_hosts=windows_workspaces"
```

## Linux Demonstration Commands

### Checking for apt updates on Ubuntu

The `check_apt_updates.yml` Ansible playbook will check for and display any outstanding updates required on your Ubuntu WorkSpaces.

It can be run with this command:

```bash
ansible-playbook ~/workspaces-with-ansible/check_apt_updates.yml -i ~/workspaces-with-ansible/workspaces_inventory.py
```

Here is an example of the output. From the below output, you can see that there are some updates which need to be performed. You also see the currently installed version, and the version which could be installed.

```bash
ssm-user@ip-10-14-1-59:/var/snap/amazon-ssm-agent/7628$ ansible-playbook ~/workspaces-with-ansible/check_apt_updates.yml -i ~/workspaces-with-ansible/workspaces_inventory.py

PLAY [Check for APT updates] *************************************************************************************************************************************************************************

TASK [Gathering Facts] *******************************************************************************************************************************************************************************
ok: [10.14.2.64]

TASK [Update APT cache] ******************************************************************************************************************************************************************************
ok: [10.14.2.64]

TASK [Check for available upgrades] ******************************************************************************************************************************************************************
changed: [10.14.2.64]

TASK [Print list of upgradable packages] *************************************************************************************************************************************************************
ok: [10.14.2.64] => {
    "apt_list.stdout_lines": [
        "Listing...",
        "apt-utils/jammy-updates 2.4.11 amd64 [upgradable from: 2.4.10]",
        "apt/jammy-updates 2.4.11 amd64 [upgradable from: 2.4.10]",
        "bind9-dnsutils/jammy-updates 1:9.18.18-0ubuntu0.22.04.1 amd64 [upgradable from: 1:9.18.12-0ubuntu0.22.04.3]",
        "bind9-host/jammy-updates 1:9.18.18-0ubuntu0.22.04.1 amd64 [upgradable from: 1:9.18.12-0ubuntu0.22.04.3]",
        "bind9-libs/jammy-updates 1:9.18.18-0ubuntu0.22.04.1 amd64 [upgradable from: 1:9.18.12-0ubuntu0.22.04.3]",
        "kpartx/jammy-updates 0.8.8-1ubuntu1.22.04.3 amd64 [upgradable from: 0.8.8-1ubuntu1.22.04.1]",
        "libapt-pkg6.0/jammy-updates 2.4.11 amd64 [upgradable from: 2.4.10]",
        "libnss-systemd/jammy-updates 249.11-0ubuntu3.11 amd64 [upgradable from: 249.11-0ubuntu3.10]",
        "libpam-systemd/jammy-updates 249.11-0ubuntu3.11 amd64 [upgradable from: 249.11-0ubuntu3.10]",
        "libsystemd0/jammy-updates 249.11-0ubuntu3.11 amd64 [upgradable from: 249.11-0ubuntu3.10]",
        "libudev1/jammy-updates 249.11-0ubuntu3.11 amd64 [upgradable from: 249.11-0ubuntu3.10]",
        "multipath-tools/jammy-updates 0.8.8-1ubuntu1.22.04.3 amd64 [upgradable from: 0.8.8-1ubuntu1.22.04.1]",
        "systemd-oomd/jammy-updates 249.11-0ubuntu3.11 amd64 [upgradable from: 249.11-0ubuntu3.10]",
        "systemd-sysv/jammy-updates 249.11-0ubuntu3.11 amd64 [upgradable from: 249.11-0ubuntu3.10]",
        "systemd/jammy-updates 249.11-0ubuntu3.11 amd64 [upgradable from: 249.11-0ubuntu3.10]",
        "ubuntu-drivers-common/jammy-updates 1:0.9.6.2~0.22.04.6 amd64 [upgradable from: 1:0.9.6.2~0.22.04.4]",
        "udev/jammy-updates 249.11-0ubuntu3.11 amd64 [upgradable from: 249.11-0ubuntu3.10]"
    ]
}

PLAY RECAP *******************************************************************************************************************************************************************************************
10.14.2.64                 : ok=4    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

### Performing apt upgrades on Ubuntu

You can use another included playbook to perform upgrades on the Ubuntu systems.

```bash
ansible-playbook ~/workspaces-with-ansible/perform_apt_upgrade.yml -i ~/workspaces-with-ansible/workspaces_inventory.py
```

After the run completes, you can re-run the `check_apt_updates.yml` playbook to validate if any updates remain.

```bash
ssm-user@ip-10-14-1-59:/var/snap/amazon-ssm-agent/7628$ ansible-playbook ~/workspaces-with-ansible/check_apt_ubuntu.yml -i ~/workspaces-with-ansible/workspaces_inventory.py

PLAY [Check for APT updates] *************************************************************************************************************************************************************************

TASK [Gathering Facts] *******************************************************************************************************************************************************************************
ok: [10.14.2.64]

TASK [Update APT cache] ******************************************************************************************************************************************************************************
ok: [10.14.2.64]

TASK [Check for available upgrades] ******************************************************************************************************************************************************************
changed: [10.14.2.64]

TASK [Print list of upgradable packages] *************************************************************************************************************************************************************
ok: [10.14.2.64] => {
    "apt_list.stdout_lines": [
        "Listing..."
    ]
}

PLAY RECAP *******************************************************************************************************************************************************************************************
10.14.2.64                 : ok=4    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

### Installing apt packages on Ubuntu

You can also install packages from the package repository easily with Ansible. This lab includes a playbook which can take a package name as an argument and install it.

```bash
ansible-playbook ~/workspaces-with-ansible/install_apt_package.sh -i ~/workspaces-with-ansible/workspaces_inventory.py -e "package_name=REPLACEME"
```

Replace the `REPLACEME` value above with the name of an Ubuntu package you would like to install from the repositories. For example, you can install KeePassXC with this command:

```bash
ansible-playbook ~/workspaces-with-ansible/install_apt_package.sh -i ~/workspaces-with-ansible/workspaces_inventory.py -e "package_name=keepassxc"
```

Successful output will look like this:

```bash
ssm-user@ip-10-0-1-139:/var/snap/amazon-ssm-agent/7628$ ansible-playbook ~/workspaces-with-ansible/install_apt_package.sh -i ~/workspaces-with-ansible/workspaces_inventory.py -e "package_name=keepassxc"
PLAY [Install a specified package on Ubuntu 22.04] *************************************************************************************************************************************

TASK [Gathering Facts] *****************************************************************************************************************************************************************
ok: [10.0.2.35]

TASK [Update apt repository cache] *****************************************************************************************************************************************************
ok: [10.0.2.35]

TASK [Install specified package] *******************************************************************************************************************************************************
changed: [10.0.2.35]

PLAY RECAP *****************************************************************************************************************************************************************************
10.0.2.35                  : ok=3    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

## Notes:

Ansible® is a registered trademark of Red Hat, Inc. in the United States and other countries.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License
This solution is licensed under the MIT-0 License.
See the [LICENSE](LICENSE) file.