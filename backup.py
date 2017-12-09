#!/usr/bin/python
import logging
from argparse import ArgumentParser, FileType
import ovirtsdk.api
from ovirtsdk.xml import params
from ovirtsdk.infrastructure import errors
import sys
import time
from vmtools import VMTools
from config import Config

"""
Main class to make the backups
"""

logger = logging.getLogger()


def initialize_logger(logger_fmt, logger_file_path, debug):
    logger_options = {
        "format": logger_fmt,
        "level": logging.DEBUG if debug else logging.INFO,
    }
    if logger_file_path:
        logger_options['filename'] = logger_file_path
    logging.basicConfig(**logger_options)

def create_argparser():
    p = ArgumentParser()
    # General options
    p.add_argument(
        "-c", "--config-file",
        help="Path to the config file, pass dash (-) for stdin",
        dest="config_file",
        required=True,
        type=FileType(),
    )
    p.add_argument(
        "-d", "--debug",
        help="Debug flag",
        dest="debug",
        action="store_true",
        default=False,
    )
    p.add_argument(
        "--dry-run",
        help="When set no operation takes effect",
        dest="dry_run",
        action="store_true",
        default=None,  # None because we need to recognize whether it was set.
    )

    osg = p.add_argument_group("oVirt server related options")
    osg.add_argument(
        "--server",
        help="URL to connect to your engine",
        dest="server",
        default=None,
    )
    osg.add_argument(
        "--username",
        help="Username to connect to the engine",
        dest="username",
        default=None,
    )
    osg.add_argument(
        "--password",
        help="Password to connect to the engine",
        dest="password",
        default=None,
    )


    vmg = p.add_argument_group("VM's related arguments")
    vmg.add_argument(
        "-a", "--all-vms",
        help="Backup all VMs and override the list of VM's in the config "
        "file",
        dest="all_vms",
        action="store_true",
        default=False,
    )
    vmg.add_argument(
        "--tag",
        help="define the tag used to override the list of VM's that should"
 	" be backed up",
	dest="vm_tag",
     	default=False,
    )
    vmg.add_argument(
        "--vm-names",
        help="List of names which VMs should be backed up",
        dest="vm_names",
        default=None,
    )
    vmg.add_argument(
        "--vm-middle",
        help="Middle part for the exported VM name",
        dest="vm_middle",
        default=None,
    )

    dcg = p.add_argument_group("Data Centrum's related options")
    dcg.add_argument(
        "--export-domain",
        help="Name of the NFS Export Domain",
        dest="export_domain",
        default=None,
    )
    dcg.add_argument(
        "--storage-domain",
        help="Storage domain where VMs are located",
        dest="storage_domain",
        default=None,
    )
    dcg.add_argument(
        "--cluster-name",
        help="Name of the cluster where VMs should be cloned",
        dest="cluster_name",
        default=None,
    )

    mscg = p.add_argument_group("Miscellaneous options")
    mscg.add_argument(
        "--snapshot-description",
        help="Description which should be set to created snapshot",
        dest="snapshot_description",
        default=None,
    )
    mscg.add_argument(
        "--timeout",
        help="Timeout in seconds to wait for time consuming operation",
        dest="timeout",
        default=None,
    )
    mscg.add_argument(
        "--backup-keep-count",
        help="Number of days to keep backups",
        dest="backup_keep_count",
        default=None,
    )
    mscg.add_argument(
        "--vm-name-max-length",
        help="Limit for length of VM's name ",
        dest="vm_name_max_length",
        default=None,
    )
    mscg.add_argument(
        "--use-short-suffix",
        help="If set it will use short suffix for VM's name",
        dest="use_short_suffix",
        action="store_true",
        default=None,
    )
    mscg.add_argument(
        "--storage-space-threshold",
        help="The number in interval (0, 1), to free space on storage domain.",
        dest="storage_space_threshold",
        type=float,
        default=None,
    )
    mscg.add_argument(
        "--persist-memorystate",
        help="If set, the VM is being paused during snapshot creation.",
        dest="persist_memorystate",
        action="store_true",
        default=None,
    )

    lg = p.add_argument_group("Logging related options")
    lg.add_argument(
        "--logger-fmt",
        help="This value is used to format log messages",
        dest="logger_fmt",
        default=None,
    )
    lg.add_argument(
        "--logger-file-path",
        help="Path to file where we to store log messages",
        dest="logger_file_path",
        default=None,
    )
    return p

def arguments_to_dict(opts):
    result = {}
    ignored_keys = ('config_file', 'dry_run', 'debug')
    for key, val in vars(opts).items():
        if key in ignored_keys:
            continue  # These doesn't have a place in config file
        if val is not None:
            result[key] = val
    return result

def main(argv):
    p = create_argparser()
    opts = p.parse_args(argv)
    config_arguments = arguments_to_dict(opts)

    global config
    with opts.config_file:
        config = Config(opts.config_file, opts.debug, config_arguments)
    initialize_logger(
        config.get_logger_fmt(), config.get_logger_file_path(), opts.debug,
    )

    time_start = int(time.time())

    has_errors = False

    # Connect to server
    connect()

    # Add all VM's to the config file
    if opts.all_vms:
        vms = api.vms.list(max=400)
        config.set_vm_names([vm.name for vm in vms])
        # Update config file
        if opts.config_file.name != "<stdin>":
            config.write_update(opts.config_file.name)
    
    # Add VM's with the tag to the vm list
    if opts.vm_tag:
	vms=api.vms.list(max=400, query="tag="+opts.vm_tag)
        config.set_vm_names([vm.name for vm in vms])
	# Update config file
        if opts.config_file.name != "<stdin>":
            config.write_update(opts.config_file.name)
		
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
            # Cleanup: Delete the cloned VM
            VMTools.delete_vm(api, config, vm_from_list)

            # Get the VM
            vm = api.vms.get(vm_from_list)
            if vm is None:
                logger.warn(
                    "The VM (%s) doesn't exist anymore, skipping backup ...",
                    vm_from_list
                )
                continue

            # Delete old backup snapshots
            VMTools.delete_snapshots(vm, config, vm_from_list)

            # Check free space on the storage
            VMTools.check_free_space(api, config, vm)

            # Create a VM snapshot:
            try:
                logger.info("Snapshot creation started ...")
                if not config.get_dry_run():
                    vm.snapshots.add(
                        params.Snapshot(
                            description=config.get_snapshot_description(),
                            vm=vm,
                            persist_memorystate=config.get_persist_memorystate(),
                        )
                    )
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
            logger.info("Clone into VM (%s) started ..." % vm_clone_name)
            if not config.get_dry_run():
                api.vms.add(params.VM(name=vm_clone_name, memory=vm.get_memory(), cluster=api.clusters.get(config.get_cluster_name()), snapshots=snapshots_param))
                VMTools.wait_for_vm_operation(api, config, "Cloning", vm_from_list)
            logger.info("Cloning finished")

            # Delete backup snapshots
            VMTools.delete_snapshots(vm, config, vm_from_list)

            # Delete old backups
            if (config.get_backup_keep_count()):
                VMTools.delete_old_backups(api, config, vm_from_list)
            if (config.get_backup_keep_count_by_number()):
                VMTools.delete_old_backups_by_number(api, config, vm_from_list)

            # Export the VM
            try:
                vm_clone = api.vms.get(vm_clone_name)
                logger.info("Export of VM (%s) started ..." % vm_clone_name)
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
        except Exception as e:
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
