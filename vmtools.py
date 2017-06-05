import logging
import ovirtsdk.api
from ovirtsdk.xml import params
from ovirtsdk.infrastructure import errors
import time
import sys
import datetime

logger = logging.getLogger()

class VMTools:
    """
    Class which holds static methods which are used more than once
    """

    @staticmethod
    def wait_for_snapshot_operation(vm, config, comment):
        """
        Wait for a snapshot operation to be finished
        :param vm: Virtual machine object
        :param config: Configuration
        :param comment: This comment will be used for debugging output
        """
        while True:
            snapshots = vm.snapshots.list(description=config.get_snapshot_description())
            if snapshots:
                if "ok" in str(snapshots[0].get_snapshot_status()):
                    break
                logger.debug("Snapshot operation(%s) in progress ...", comment)
                time.sleep(config.get_timeout())
            else:
                break

    @staticmethod
    def delete_snapshots(vm, config, vm_name):
        """
        Deletes a backup snapshot
        :param vm: Virtual machine object
        :param config: Configuration
        """
        snapshots = vm.snapshots.list(description=config.get_snapshot_description())
        done = False
        if snapshots:
            logger.debug("Found snapshots(%s):", len(snapshots))
            for i in snapshots:
                if snapshots:
                    logger.debug("Snapshots description: %s, Created on: %s", i.get_description(), i.get_date())
                    for i in snapshots:
                        try:
                            while True:
                                try:
                                    if not config.get_dry_run():
                                        i.delete()
                                    logger.info("Snapshot deletion started ...")
                                    VMTools.wait_for_snapshot_operation(vm, config, "deletion")
                                    done = True
                                    break
                                except Exception as e:
                                    if "status: 409" in str(e):
                                        logger.debug("Got 409 wait for operation to be finished, DEBUG: %s", e)
                                        time.sleep(config.get_timeout())
                                        continue
                                    else:
                                        logger.info("  !!! Found another exception for VM: %s", vm_name)
                                        logger.info("  DEBUG: %s", e)
                                        sys.exit(1)
                        except Exception as e:
                            logger.info("  !!! Can't delete snapshot for VM: %s", vm_name)
                            logger.info("  Description: %s, Created on: %s", i.get_description(), i.get_date())
                            logger.info("  DEBUG: %s", e)
                            sys.exit(1)
            if done:
                logger.info("Snapshots deleted")

    @staticmethod
    def delete_vm(api, config, vm_name):
        """
        Delets a vm which was created during backup
        :param vm: Virtual machine object
        :param config: Configuration
        """
        i_vm_name = ""
        done = False
        try:
            vm_search_regexp = ("name=%s%s*" % (vm_name, config.get_vm_middle()))
            for i in api.vms.list(query=vm_search_regexp):
                i_vm_name = str(i.get_name())
                logger.info("Delete cloned VM (%s) started ..." % i_vm_name)
                if not config.get_dry_run():
                    vm = api.vms.get(i_vm_name)
                    if vm is None:
                        logger.warn(
                            "The VM (%s) doesn't exist anymore, "
                            "skipping deletion ...", i_vm_name
                        )
                        done = True
                        continue
                    vm.delete_protected = False
                    vm = vm.update()
                    vm.delete()
                    while api.vms.get(i_vm_name) is not None:
                        logger.debug("Deletion of cloned VM (%s) in progress ..." % i_vm_name)
                        time.sleep(config.get_timeout())
                    done = True
        except Exception as e:
            logger.info("!!! Can't delete cloned VM (%s)", i_vm_name)
            raise e
        if done:
            logger.info("Cloned VM (%s) deleted" % i_vm_name)

    @staticmethod
    def wait_for_vm_operation(api, config, comment, vm_name):
        """
        Wait for a vm operation to be finished
        :param vm: Virtual machine object
        :param config: Configuration
        :param comment: This comment will be used for debugging output
        """
        composed_vm_name = "%s%s%s" % (
            vm_name, config.get_vm_middle(), config.get_vm_suffix()
        )
        while True:
            vm = api.vms.get(composed_vm_name)
            if vm is None:
                logger.warn(
                    "The VM (%s) doesn't exist anymore, "
                    "leaving waiting loop ...", composed_vm_name
                )
                break

            vm_status = str(vm.get_status().state).lower()
            if vm_status == "down":
                break
            logger.debug(
                "%s in progress (VM %s status is '%s') ...",
                comment, composed_vm_name, vm_status,
            )
            time.sleep(config.get_timeout())

    @staticmethod
    def delete_old_backups(api, config, vm_name):
        """
        Delete old backups from the export domain
        :param api: ovirtsdk api
        :param config: Configuration
        """
	storage_domain = config.get_export_domain()
        vm_search_regexp = ("%s%s*" % (vm_name, config.get_vm_middle())).encode('ascii', 'ignore')
	old_vms = []
        for vm in api.storagedomains.get(storage_domain).vms.list(name=vm_search_regexp):
	    old_vms.append(vm.get_name())
        delete_vms = sorted(old_vms)[:-config.get_backup_keep_count()]
	for vm_name in delete_vms:
	    vm = api.storagedomains.get(storage_domain).vms.get(vm_name)
            logger.info("Backup deletion started for backup: %s", vm.get_name())
            if not config.get_dry_run():
                vm.delete()
                while api.storagedomains.get(storage_domain).vms.get(vm_name) is not None:
                    logger.debug("Delete old backup (%s) in progress ..." % vm_name)
                    time.sleep(config.get_timeout())

    @staticmethod
    def delete_old_templates(api, config, vm_name):
        """
        Delete old template backups 
        :param api: ovirtsdk api
        :param config: Configuration
        """
        vm_search_regexp = ("%s%s*" % (vm_name, config.get_vm_middle())).encode('ascii', 'ignore')
	storage_domain = config.get_destination_domain()
	old_templates = []
        for t in api.templates.list(name=vm_search_regexp):
	    old_templates.append(t.get_name())
        delete_templates = sorted(old_templates)[:-config.get_backup_keep_count()]
	for t_name in delete_templates:
	    t = api.templates.get(t_name)
            logger.info("Template deletion started for backup: %s", t_name)
            if not config.get_dry_run():
                t.delete()
                while api.templates.get(vm_name) is not None:
                    logger.debug("Delete old template (%s) in progress ..." % t_name)
                    time.sleep(config.get_timeout())

    @staticmethod
    def create_snapshot(api, config, vm_from_list):
        """
        Create snapshot of given vm
        :param api: ovirtsdk api
        :param config: Configuration
	:vm: VM to snapshot
        """
        vm = api.vms.get(vm_from_list)
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

    @staticmethod
    def clone_snapshot(api, config, vm_from_list):
        """
        Clone snapshot into a new vm
        :param api: ovirtsdk api
        :param config: Configuration
	:vm: VM to clone
        """
        vm_clone_name = vm_from_list + config.get_vm_middle() + config.get_vm_suffix()
        vm = api.vms.get(vm_from_list)
        snapshots = vm.snapshots.list(description=config.get_snapshot_description())
        if not snapshots:
            logger.error("!!! No snapshot found !!!")
            has_errors = True
        snapshot=snapshots[0]

        # Find the storage domain where the disks should be created:
        sd = api.storagedomains.get(name=config.get_destination_domain())

        # Find the image identifiers of the disks of the snapshot, as
        # we need them in order to explicitly indicate that we want
        # them created in a different storage domain:
        disk_ids = []
        for current in snapshot.disks.list():
            disk_ids.append(current.get_id())
        # Prepare the list of disks for the operation to create the
        # snapshot,explicitly indicating for each of them the storage
        # domain where it should be created:
        disk_list = []
        for disk_id in disk_ids:
            disk = params.Disk(
                image_id=disk_id,
                storage_domains=params.StorageDomains(
                  storage_domain=[
                    params.StorageDomain(
                      id=sd.get_id(),
                    ),
                  ],
                ),
            )
            disk_list.append(disk)

        snapshot_param = params.Snapshot(id=snapshot.id)
        snapshots_param = params.Snapshots(snapshot=[snapshot_param])
        logger.info("Clone into VM (%s) started ..." % vm_clone_name)
        if not config.get_dry_run():
            api.vms.add(params.VM(
                            name=vm_clone_name,
                            memory=vm.get_memory(),
                            cluster=api.clusters.get(config.get_cluster_name()),
                            snapshots=snapshots_param,
                            disks=params.Disks(
                               disk=disk_list,
                            )
                        )
            )
            VMTools.wait_for_vm_operation(api, config, "Cloning", vm_from_list)
        logger.info("Cloning finished")

    @staticmethod
    def backup_to_export(api, config, vm_from_list):
        """
        Export snaphot to en export domain
        :param api: ovirtsdk api
        :param config: Configuration
	:vm_name: Name of VM to backup
        """
        vm_clone_name = vm_from_list + config.get_vm_middle() + config.get_vm_suffix()
        vm_clone = api.vms.get(vm_clone_name)
        logger.info("Export of VM (%s) started ..." % vm_clone_name)
        if not config.get_dry_run():
            vm_clone.export(params.Action(storage_domain=api.storagedomains.get(config.get_export_domain())))
            VMTools.wait_for_vm_operation(api, config, "Exporting", vm_from_list)
        logger.info("Exporting finished")

    @staticmethod
    def backup_to_template(api, config, vm_from_list):
        """
        Create template from cloned vm
        :param api: ovirtsdk api
        :param config: Configuration
	:vm_name: Name of VM to backup
        """
        vm_clone_name = vm_from_list + config.get_vm_middle() + config.get_vm_suffix()
        vm_clone = api.vms.get(vm_clone_name)
        logger.info("Creation of template from VM (%s) started ..." % vm_clone_name)
        if not config.get_dry_run():
            api.templates.add(params.Template(name=vm_clone_name, vm=vm_clone))
            VMTools.wait_for_vm_operation(api, config, "Creating template", vm_from_list)
        logger.info("Template creation finished")


    @staticmethod
    def check_free_space(api, config, vm):
        """
        Check if the summarized size of all VM disks is available on the storagedomain
        to avoid running out of space
        """
        sd = api.storagedomains.get(config.get_storage_domain())
        vm_size = 0
        for disk in vm.disks.list():
            # For safety reason "vm.actual_size" is not used
            if disk.size is not None:
                vm_size += disk.size
        storage_space_threshold = 0
        if config.get_storage_space_threshold() > 0:
            storage_space_threshold = config.get_storage_space_threshold()
        vm_size *= (1 + storage_space_threshold)
        if (sd.available - vm_size) <= 0:
            raise Exception("!!! The is not enough free storage on the storage domain '%s' available to backup the VM '%s'" % (config.get_storage_domain(), vm.name))
