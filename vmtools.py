import logging
import time
import sys
import datetime
import operator

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
        vm_search_regexp = ("%s%s*" % (vm_name, config.get_vm_middle())).encode('ascii', 'ignore')
        exported_vms = api.storagedomains.get(config.get_export_domain()).vms.list(name=vm_search_regexp)
        for i in exported_vms:
            vm_name_export = str(i.get_name())
            datetimeStart = datetime.datetime.combine((datetime.date.today() - datetime.timedelta(config.get_backup_keep_count())), datetime.datetime.min.time())
            timestampStart = time.mktime(datetimeStart.timetuple())
            datetimeCreation = i.get_creation_time()
            datetimeCreation = datetimeCreation.replace(hour=0, minute=0, second=0)
            timestampCreation = time.mktime(datetimeCreation.timetuple())
            if timestampCreation < timestampStart:
                logger.info("Backup deletion started for backup: %s", vm_name_export)
                if not config.get_dry_run():
                    i.delete()
                    while api.storagedomains.get(vm_name_export) is not None:
                        logger.debug("Delete old backup (%s) in progress ..." % vm_name_export)
                        time.sleep(config.get_timeout())

    @staticmethod
    def delete_old_backups_by_number(api, config, vm_name):
        """
        Delete old backups from the export domain by number of requested
        :param api: ovirtsdk api
        :param config: Configuration
        """
        vm_search_regexp = ("%s%s*" % (vm_name, config.get_vm_middle())).encode('ascii', 'ignore')
        exported_vms = api.storagedomains.get(config.get_export_domain()).vms.list(name=vm_search_regexp)
        exported_vms.sort(key=lambda x: x.get_creation_time())
        while len(exported_vms) > config.get_backup_keep_count_by_number():
            i = exported_vms.pop(0)
            vm_name_export = str(i.get_name())
            logger.info("Backup deletion started for backup: %s", vm_name_export)
            if not config.get_dry_run():
                i.delete()
                while api.storagedomains.get(vm_name_export) is not None:
                    logger.debug("Delete old backup (%s) in progress ..." % vm_name_export)
                    time.sleep(config.get_timeout())

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
