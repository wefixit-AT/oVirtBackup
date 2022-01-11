# oVirtBackup

This is a tool, written in Python, to make **online** fullbackup's of a VM which runs in an oVirt environment.

## Requirements

This release was tested on oVirt 4.3

It is necessary to install the oVirt Python-sdk.
In addition when running Pyhon < 2.7 you need you install argparse.

[http://www.ovirt.org/Python-sdk](http://www.ovirt.org/Python-sdk)

## Usage

Take a look at the usage text.

    backup.py -h

## Configuration

Take a look at the example "config_example.cfg"

Please avoid Cirillic symbols in the configuration otherwise you will get an exception see [#59](https://github.com/wefixit-AT/oVirtBackup/issues/59)

## Workflow

* Create a snapshot
* Clone the snapshot into a new VM
* Delete the snapshot
* Delete previous backups (if set)
* Export the VM to the NFS share
* Delete the VM

## Installation

Environment:

* CentOS 7.9.2009
* selinux enforcing
* Python 2.7.5

```console
git clone https://github.com/wefixit-AT/oVirtBackup.git /opt/oVirtBackup.git
yum install https://resources.ovirt.org/pub/yum-repo/ovirt-release43.rpm
yum install python-ovirt-engine-sdk4
yum install python-configparser
mkdir /etc/oVirtBackup
cp /opt/oVirtBackup.git/config_example.cfg /etc/oVirtBackup/config.cfg
```

Prepare /etc/oVirtBackup/config.cfg

	/opt/oVirtBackup.git/backup.py -c /etc/oVirtBackup/config.cfg

## Useful tips

### crontab

	00  20  *   *   *   /home/backup/oVirtBackup.git/backup.py -c /home/backup/oVirtBackup.git/config_webserver.cfg -d >> /var/log/oVirtBackup/webserver.log 

Logrotate: /etc/logrotate.d/oVirtBackup

	/var/log/oVirtBackup/* {
    	daily
    	rotate 14
    	compress
    	delaycompress
    	missingok
    	notifempty
	}
	
### Security

Set permissions to config.cfg only for the needed user (chmod 600 config.cfg).

## TODO's

* When the ovirtsdk supports exporting a snapshot directly to a domain, the step of a VM creation can be removed to save some disk space during backup

## Useful links:

* [http://www.ovirt.org/REST-Api](http://www.ovirt.org/REST-Api)
* [http://www.ovirt.org/Python-sdk](http://www.ovirt.org/Python-sdk)
* [http://www.ovirt.org/Testing/PythonApi](http://www.ovirt.org/Testing/PythonApi)
* [https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Virtualization/3.1/html-single/Developer_Guide/files/ovirtsdk.infrastructure.brokers.html#VMSnapshot](https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Virtualization/3.1/html-single/Developer_Guide/files/ovirtsdk.infrastructure.brokers.html#VMSnapshot)

## Running tests

Install [tox](http://tox.readthedocs.io/en/latest/index.html).

```sh
$ tox
```

## FIXES
The script does not delete the cloned VM
https://github.com/wefixit-AT/oVirtBackup/issues/67
https://github.com/wefixit-AT/oVirtBackup/issues/66

A comment in https://github.com/wefixit-AT/oVirtBackup/pull/72/commits/959b5fb376b5d951afdd8bef2ec2352ec421f415 suggested a fix for vmtools.py for a line of coded which was present in master and not included in the branches.
I copied the relevant file to oVirt4.3 branch and changed the line as pointed out in the commit and everything worked as expected
