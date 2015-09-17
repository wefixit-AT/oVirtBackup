# oVirtBackup

This is a tool, written in Python, to make **online** fullbackup's of a VM which runs in an oVirt environment.

## Usage

backup.py -c config.cfg -d

	-c ... Path to the config file
	-d ... Debug flag

## Configuration

Take a look at the example "config_example.cfg"

## Workflow

* Create a snapshot
* Clone the snapshot into a new VM
* Delete the snapshot
* Export the VM to the NFS share
* Delete the VM

## TODO's

* When the ovirtsdk supports exporting a snapshot directly to a domain, the step of a VM creation can be removed to save some disk space during backup

## Usefull links:

* http://www.ovirt.org/REST-Api
* http://www.ovirt.org/Python-sdk
* http://www.ovirt.org/Testing/PythonApi
* https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Virtualization/3.1/html-single/Developer_Guide/files/ovirtsdk.infrastructure.brokers.html#VMSnapshot