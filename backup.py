#!/usr/bin/python
import logging
from argparse import ArgumentParser, FileType
import ovirtsdk4 as sdk
import ovirtsdk4.types as types
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

    dsk = p.add_argument_group("VM's disks arguments")
    dsk.add_argument(
        "--bootable_only",
        help="Backup Bootable Disk Only",
        dest="bootable_only",
        default=None,
    )
    dsk.add_argument(
        "--with_disks_deactivated",
        help="Backup deactivated disks",
        dest="with_disks_deactivated",
        default=None,
    )
    dsk.add_argument(
        "--disks_id_exclude",
        help="an array of exclude disks id",
        dest="disks_id_exclude",
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
        "--datacenter-name",
        help="Datacenter where export domain is attached",
        dest="datacenter_name",
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

    system_service=api.system_service()

    # Test if data center is valid
    # Retrieve the data center service:
    if  system_service.data_centers_service().list(search='name=%s' % config.get_datacenter_name() )[0] is None:
        logger.error("!!! Check the datacenter_name in the config")
        api.close()
        sys.exit(1)
    # Test if config export_domain is valid
    if system_service.storage_domains_service().list(search='name=%s' % config.get_export_domain() )[0] is None:
        logger.error("!!! Check the export_domain in the config " + config.get_export_domain())
        api.close()
        sys.exit(1)

    # Test if config cluster_name is valid
    if system_service.clusters_service().list(search='name=%s' % config.get_cluster_name() )[0] is None:
        logger.error("!!! Check the cluster_name in the config")
        api.close()
        sys.exit(1)

    # Test if config storage_domain is valid
    if system_service.storage_domains_service().list(search='name=%s' % config.get_storage_domain() )[0] is None:
        logger.error("!!! Check the storage_domain in the config")
        api.close()
        sys.exit(1)

    vms_service=system_service.vms_service()

    # Add all VM's to the config file
    if opts.all_vms:
        vms = vms_service.list(max=400)
        config.set_vm_names([vm.name for vm in vms])
        # Update config file
        if opts.config_file.name != "<stdin>":
            config.write_update(opts.config_file.name)
    # Add VM's with the tag to the vm list
    if opts.vm_tag:
        vms = vms_service.list(max=400, search="tag="+opts.vm_tag)
        config.set_vm_names([vm.name for vm in vms])
        # Update config file
        if opts.config_file.name != "<stdin>":
            config.write_update(opts.config_file.name)

    # Test if all VM names are valid
    for vm_from_list in config.get_vm_names():
        if vms_service.list(search='name=%s' % str(vm_from_list)) is None:
            logger.error("!!! There are no VM with the following name in your cluster: %s", vm_from_list)
            api.close()
            sys.exit(1)

    # Test if config vm_middle is valid
    if not config.get_vm_middle():
        logger.error("!!! It's not valid to leave vm_middle empty")
        api.close()
        sys.exit(1)

    vms_with_failures = list(config.get_vm_names())


    dcs_service = system_service.data_centers_service()
    dc = dcs_service.list(search='name=%s' % config.get_datacenter_name() )[0]
    dc_service = dcs_service.data_center_service(dc.id)
    sds_service = dc_service.storage_domains_service()
    sd_service = sds_service.list(search='name=%s' % config.get_export_domain())[0]

    for vm_from_list in config.get_vm_names():
        config.clear_vm_suffix()
        vm_clone_name = vm_from_list + config.get_vm_middle() + config.get_vm_suffix()

        # Check VM name length limitation
        length = len(vm_clone_name)
        if length > config.get_vm_name_max_length():
            logger.error("!!! VM name with middle and suffix are to long (size: %s, allowed %s) !!!", length, config.get_vm_name_max_length())
            logger.info("VM name: %s", vm_clone_name)
            api.close()
            sys.exit(1)

        logger.info("Start backup for: %s", vm_from_list)
        try:
            VMTools.check_storage_domain_status(
                api,
                config.get_datacenter_name(),
                config.get_export_domain()
            )
            # Cleanup: Delete the cloned VM
            VMTools.delete_vm(api, config, vm_from_list)

            # Get the VM
            vm = vms_service.list(search='name=%s' % str(vm_from_list))
            if len(vm) == 0 :
                logger.warn(
                    "The VM (%s) doesn't exist anymore, skipping backup ...",
                    vm_from_list
                )
                continue

            vm=vm[0]

            # Get the Attachments Disk
            disk_attachments = vms_service.vm_service(vm.id).disk_attachments_service().list()
            disksBackup = []
            BootableOnly = config.get_bootable_only()
            for disk_attachment in disk_attachments:
                if BootableOnly:
                    if disk_attachment.bootable == True:
                        disksBackup.append(disk_attachment)
                        break
                elif config.get_with_disks_deactivated() or disk_attachment.active:
                    disksBackup.append(disk_attachment)

            if not BootableOnly:
                disks_id_exclude=config.get_disks_id_exclude()
                if disks_id_exclude:
                    disksBackup = [disk for disk in disksBackup if disk.id not in disks_id_exclude]

            for disk_attachment in disksBackup:
                if disk_attachment.bootable == True:
                    logger.info("Finding bootable disk: %s", disk_attachment.id)
                else:
                    logger.info("Finding disk: %s", disk_attachment.id)
#                print disk_attachment.id
#            break
#            print disks_id[0].__dict__

            # Delete old backup snapshots
            VMTools.delete_snapshots(api, vm, config, vm_from_list)

            # Check free space on the storage
            VMTools.check_free_space(api, config, vm)

            # Create a VM snapshot:
            try:
                logger.info("Snapshot creation started ...")
                snapshots_service = vms_service.vm_service(vm.id).snapshots_service()
                if not config.get_dry_run():
                    # Add the new snapshot:
                    snapshots_service.add(
                        types.Snapshot(
                            description=config.get_snapshot_description(),
                            persist_memorystate=config.get_persist_memorystate(),
                            disk_attachments=disksBackup,
                        ),
                    )
                    VMTools.wait_for_snapshot_operation(api,vm, config, "creation")
                logger.info("Snapshot created")
            except Exception as e:
                logger.info("Can't create snapshot for VM: %s", vm_from_list)
                logger.info("DEBUG: %s", e)
                has_errors = True
                continue
            # Workaround for some SDK problems see issue #17
            time.sleep(config.get_timeout())

            # Clone the snapshot into a VM
            snapshots = snapshots_service.list()
            snap = None
            for i in snapshots:
                if i.description == config.get_snapshot_description():
                    snap=i

            if not snap:
                logger.error("!!! No snapshot found !!!")
                has_errors = True
                continue

            logger.info("Clone into VM (%s) started ..." % vm_clone_name)
            if not config.get_dry_run():
                cloned_vm = vms_service.add(
                    vm=types.Vm(
                    name=vm_clone_name, 
                    memory=vm.memory,
                    snapshots=[
                        types.Snapshot(
                            id=snap.id
                        )
                    ],
                    cluster=types.Cluster(
                        name=config.get_cluster_name()
                        )
                    )
                )
                # Find the service that manages the cloned virtual machine:
                cloned_vm_service = vms_service.vm_service(cloned_vm.id)
                # Wait till the virtual machine is down, as that means that the creation
                # of the disks of the virtual machine has been completed:
                while True:
                    time.sleep(config.get_timeout())
                    logger.debug("Cloning into VM (%s) in progress ..." % vm_clone_name)
                    cloned_vm = cloned_vm_service.get()
                    if cloned_vm.status == types.VmStatus.DOWN:
                         break

            logger.info("Cloning finished")

            # Delete backup snapshots
            VMTools.delete_snapshots(api, vm, config, vm_from_list)

            # Delete old backups
            if (config.get_backup_keep_count()):
                VMTools.delete_old_backups(api, config, vm_from_list)
            if (config.get_backup_keep_count_by_number()):
                VMTools.delete_old_backups_by_number(api, config, vm_from_list)

            # Export the VM
            try:
                vm_clone = api.system_service().vms_service().list(search='name=%s' % str(vm_clone_name))[0]
                logger.info("Export of VM (%s) started ..." % vm_clone_name)
                if not config.get_dry_run():
                    cloned_vm_service = vms_service.vm_service(vm_clone.id)
                    cloned_vm_service.export(
                        exclusive=True,
                        discard_snapshots=True,
                        storage_domain=types.StorageDomain(
                            name=config.get_export_domain()
                        )
                    )
                    while True:
                        time.sleep(config.get_timeout())
                        cloned_vm = cloned_vm_service.get()
                        if cloned_vm.status == types.VmStatus.DOWN:
                            break

                logger.info("Exporting finished")
            except Exception as e:
                logger.info("Can't export cloned VM (%s) to domain: %s", vm_clone_name, config.get_export_domain())
                logger.info("DEBUG: %s", e)
                has_errors = True
                continue

            # Delete the CLONED VM
            VMTools.delete_vm(api, config, vm_from_list)

            time_end = int(time.time())
            time_diff = (time_end - time_start)
            time_minutes = int(time_diff / 60)
            time_seconds = time_diff % 60

            logger.info("Duration: %s:%s minutes", time_minutes, time_seconds)
            logger.info("VM exported as %s", vm_clone_name)
            logger.info("Backup done for: %s", vm_from_list)
            vms_with_failures.remove(vm_from_list)
        except Exception as e:
            logger.error("!!! Got unexpected exception: %s", e)
            api.close()
            sys.exit(1)

    logger.info("All backups done")

    if vms_with_failures:
        logger.info("Backup failured for:")
        for i in vms_with_failures:
            logger.info("  %s", i)

    if has_errors:
        logger.info("Some errors occured during the backup, please check the log file")
        api.close()
        sys.exit(1)

    # Disconnect from the server
    api.close()

def connect():
    global api
    api = sdk.Connection(
            url=config.get_server(),
            username=config.get_username(),
            password=config.get_password(),
            insecure=True,
            debug=False
            )

if __name__ == "__main__":
    main(sys.argv[1:])
