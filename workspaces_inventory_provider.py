#!/usr/bin/env python3

import argparse
import json
import os
import boto3
from botocore.config import Config

def generate_inventory(workspaces):
    inventory = {'_meta': {'hostvars': {}}}
    for ws in workspaces:
        state = ws.get('State', '')
        if state != 'AVAILABLE':
            continue

        computer_name = ws.get('ComputerName', '')
        os = ws.get('WorkspaceProperties', {}).get('OperatingSystemName', '')

        if os == 'UBUNTU_22_04':
            group_name = 'ubuntu_22_04_workspaces'
        elif os == 'AMAZON_LINUX_2':
            group_name = 'amazon_linux_2_workspaces'
        elif os == 'WINDOWS_SERVER_2016':
            group_name = 'windows_server_2016_workspaces'
        elif os == 'WINDOWS_SERVER_2019':
            group_name = 'windows_server_2019_workspaces'
        elif os == 'WINDOWS_SERVER_2022':
            group_name = 'windows_server_2022_workspaces'
        elif os == 'WINDOWS_10':
            group_name = 'windows_10_workspaces'
        elif os == 'WINDOWS_11':
            group_name = 'windows_11_workspaces'
        else:
            print(f"Warning: WorkSpace ({ws}) is running an operating system that is not supported by the dynamic inventory provider. See the GitHub page for support.")
            continue

        ip_address = ws.get('IpAddress', '')

        if group_name not in inventory:
            inventory[group_name] = {'hosts': [], 'vars': {}}

        inventory[group_name]['hosts'].append(ip_address)

        if group_name.startswith('windows'):
            host_vars = {
                'ansible_connection': 'winrm',
                'ansible_winrm_transport': 'kerberos',
                'ansible_winrm_port': '5985',
                'ansible_winrm_kerberos_hostname_override': computer_name
            }
        else:
            host_vars = {
                'ansible_connection': 'ssh',
                'ansible_user': 'ansible'
            }

        inventory['_meta']['hostvars'][ip_address] = host_vars

    return inventory

def main():
    parser = argparse.ArgumentParser(description='Generate Ansible inventory for AWS WorkSpaces.')
    parser.add_argument('--region', help='AWS Region')
    parser.add_argument('--list', action='store_true', help='List inventory.')
    exclusivearguments = parser.add_mutually_exclusive_group()
    exclusivearguments.add_argument('--directory-id', help='DirectoryId.')
    exclusivearguments.add_argument('--workspace-ids', nargs='*', help='One or more WorkSpace IDs, separated by space.')
    args = parser.parse_args()

# If neither the --list nor --workspace-id argument was used, print the help text

    if not args.list and not args.workspace_ids:
        parser.print_help()
        return
# When directly calling this script, the region and directory ID can be specified as arguments.
# However, if this script is being used with `ansible-inventory`, these must be set as environment variables
# For example: `export AWS_REGION=us-west-2` or `export DIRECTORY_ID=d-xxxxxxxxx`
# Clear variables with `unset AWS_REGION` or `unset DIRECTORY_ID`

    region = args.region if args.region else os.environ.get('AWS_REGION')

    if not region:
        print('Error: AWS region must be specified via --region argument or AWS_REGION environment variable.')
        exit(1)

    workspaces_directory = args.directory_id if args.directory_id else os.environ.get('DIRECTORY_ID')

    specific_workspaces = args.workspace_ids

    config = Config(
        retries = {
            'max_attempts': 10,
            'mode': 'standard'
        }
    )

    client = boto3.client('workspaces', config=config, region_name=region)
    paginator = client.get_paginator("describe_workspaces")

    if specific_workspaces:
        operation_parameters= {
            "WorkspaceIds": specific_workspaces
            }
        workspaces = []
        for page in paginator.paginate(
            **operation_parameters, PaginationConfig={"PageSize": 25}
        ):
            workspaces.extend(page['Workspaces'])

    elif workspaces_directory:
        operation_parameters = {
            "DirectoryId": workspaces_directory
            }
        workspaces = []
        for page in paginator.paginate(
            **operation_parameters, PaginationConfig={"PageSize": 25}
        ):
            workspaces.extend(page['Workspaces'])
    else:
        workspaces = []
        for page in paginator.paginate(
            PaginationConfig={"PageSize": 25}
        ):
            workspaces.extend(page['Workspaces'])

    inventory = generate_inventory(workspaces)

    if args.list:
        print(json.dumps(inventory, indent=4))
    elif args.workspace_ids:
        print(json.dumps(inventory, indent=4))

if __name__ == '__main__':
    main()
