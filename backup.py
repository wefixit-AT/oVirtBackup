#!/usr/bin/python
import logging
import ovirtsdk.api
from ovirtsdk.xml import params
from ovirtsdk.infrastructure import errors
import sys
import time
from vmtools import VMTools
from config import Config
from getopt import getopt, GetoptError
import vmlist

"""
Main class to make the backups
"""

logger = logging.getLogger()


def usage():
    print "Usage: backup.py -c <config.cfg> [-a] [-d] [-h]"
    print "\t-c\tPath to the config file"
    print "\t-a\tBackup all VM's and override the list of VM's in the config file"
    print "\t-d\tDebug flag"
    print "\t-h\tDisplay this help and exit"
    sys.exit(0)

def initialize_logger(logger_fmt, logger_file_path, debug):
    logger_options = {
        "format": logger_fmt,
        "level": logging.DEBUG if debug else logging.INFO,
    }
    if logger_file_path:
        logger_options['filename'] = logger_file_path
    logging.basicConfig(**logger_options)

def main(argv):
    try:
        opts, args = getopt(argv, "hac:d")
        debug = False
        all_vms = False
        if not opts:
            usage()
        for opt, arg in opts:
            if (opt == "-h") or (opt == "--help"):
                usage()
            elif opt in ("-c"):
                config_file = arg
            elif opt in ("-d"):
                debug = True
            elif opt in ("-a"):
                all_vms = True
    except GetoptError:
        usage()

    global config
    config = Config(config_file, debug)
    initialize_logger(
        config.get_logger_fmt(), config.get_logger_file_path(), debug,
    )

    time_start = int(time.time())

    has_errors = False

    # Connect to server
    connect()

    # Add all VM's to the config file
    if all_vms:
        vms=api.vms.list(max=400)
        vmlist.get_vm_list(vms,config_file)
        config = Config(config_file, debug)

    # Test if config export_domain is valid
    if api.storagedomains.get(config.get_export_domain()) is None:
        logger.error("!!! Check the export_domain in the config")
        api.disconnect()
        sys.exit(1)

    # Test if config cluster_name is valid
    if api.clusters.get(config.get_cluster_name()) is None:
        logger.error("!!! Check the cluster_name in the config")
        api.disconnect()
        sys.exit(1)

    # Test if config storage_domain is valid
    if api.storagedomains.get(config.get_storage_domain()) is None:
        logger.error("!!! Check the storage_domain in the config")
        api.disconnect()
        sys.exit(1)

    # Test if all VM names are valid
    for vm_from_list in config.get_vm_names():
        if not api.vms.get(vm_from_list):
            logger.error("!!! There are no VM with the following name in your cluster: %s", vm_from_list)
            api.disconnect()
            sys.exit(1)

    # Test if config vm_middle is valid
    if not config.get_vm_middle():
        logger.error("!!! It's not valid to leave vm_middle empty")
        api.disconnect()
        sys.exit(1)

    vms_with_failures = list(config.get_vm_names())

    for vm_from_list in config.get_vm_names():
        config.clear_vm_suffix()
        vm_clone_name = vm_from_list + config.get_vm_middle() + config.get_vm_suffix()

        # Check VM name length limitation
        length = len(vm_clone_name)
        if length > config.get_vm_name_max_length():
            logger.error("!!! VM name with middle and suffix are to long (size: %s, allowed %s) !!!", length, config.get_vm_name_max_length())
            logger.info("VM name: %s", vm_clone_name)
            api.disconnect()
            sys.exit(1)

        logger.info("Start backup for: %s", vm_from_list)
        try:
            # Get the VM
            vm = api.vms.get(vm_from_list)

            # Cleanup: Delete the cloned VM
            VMTools.delete_vm(api, config, vm_from_list)

            # Delete old backup snapshots
            VMTools.delete_snapshots(vm, config, vm_from_list)

            # Check free space on the storage
            VMTools.check_free_space(api, config, vm)

            # Create a VM snapshot:
            try:
                logger.info("Snapshot creation started ...")
                if not config.get_dry_run():
                    vm.snapshots.add(params.Snapshot(description=config.get_snapshot_description(), vm=vm))
                    VMTools.wait_for_snapshot_operation(vm, config, "creation")
                logger.info("Snapshot created")
            except Exception as e:
                logger.info("Can't create snapshot for VM: %s", vm_from_list)
                logger.info("DEBUG: %s", e)
                has_errors = True
                continue
            # Workaround for some SDK problems see issue #17
            time.sleep(10)

            # Clone the snapshot into a VM
            snapshots = vm.snapshots.list(description=config.get_snapshot_description())
            if not snapshots:
                logger.error("!!! No snapshot found !!!")
                has_errors = True
                continue
            snapshot_param = params.Snapshot(id=snapshots[0].id)
            snapshots_param = params.Snapshots(snapshot=[snapshot_param])
            logger.info("Clone into VM started ...")
            if not config.get_dry_run():
                api.vms.add(params.VM(name=vm_clone_name, memory=vm.get_memory(), cluster=api.clusters.get(config.get_cluster_name()), snapshots=snapshots_param))
                VMTools.wait_for_vm_operation(api, config, "Cloning", vm_from_list)
            logger.info("Cloning finished")

            # Delete backup snapshots
            VMTools.delete_snapshots(vm, config, vm_from_list)

            # Delete old backups
            VMTools.delete_old_backups(api, config, vm_from_list)

            # Export the VM
            try:
                vm_clone = api.vms.get(vm_clone_name)
                logger.info("Export started ...")
                if not config.get_dry_run():
                    vm_clone.export(params.Action(storage_domain=api.storagedomains.get(config.get_export_domain())))
                    VMTools.wait_for_vm_operation(api, config, "Exporting", vm_from_list)
                logger.info("Exporting finished")
            except Exception as e:
                logger.info("Can't export cloned VM (%s) to domain: %s", vm_clone_name, config.get_export_domain())
                logger.info("DEBUG: %s", e)
                has_errors = True
                continue

            # Delete the VM
            VMTools.delete_vm(api, config, vm_from_list)

            time_end = int(time.time())
            time_diff = (time_end - time_start)
            time_minutes = int(time_diff / 60)
            time_seconds = time_diff % 60

            logger.info("Duration: %s:%s minutes", time_minutes, time_seconds)
            logger.info("VM exported as %s", vm_clone_name)
            logger.info("Backup done for: %s", vm_from_list)
            vms_with_failures.remove(vm_from_list)
        except errors.ConnectionError as e:
            logger.error("!!! Can't connect to the server %s", e)
            connect()
            continue
        except errors.RequestError as e:
            logger.error("!!! Got a RequestError: %s", e)
            has_errors = True
            continue
        except  Exception as e:
            logger.error("!!! Got unexpected exception: %s", e)
            api.disconnect()
            sys.exit(1)

    logger.info("All backups done")

    if vms_with_failures:
        logger.info("Backup failured for:")
        for i in vms_with_failures:
            logger.info("  %s", i)

    if has_errors:
        logger.info("Some errors occured during the backup, please check the log file")
        api.disconnect()
        sys.exit(1)

    # Disconnect from the server
    api.disconnect()

def connect():
    global api
    api = ovirtsdk.api.API(
        url=config.get_server(),
        username=config.get_username(),
        password=config.get_password(),
        insecure=True,
        debug=False
    )

if __name__ == "__main__":
   main(sys.argv[1:])
