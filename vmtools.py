import time 
import sys
import datetime
from logger import Logger

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
                if config.get_debug():
                    Logger.log("Snapshot operation(" + comment + ") in progress ...")
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
            if config.get_debug():
                Logger.log("Found snapshots(" + str(len(snapshots)) + "):")
            for i in snapshots:
                if snapshots:
                    if config.get_debug():
                        Logger.log("Snapshots description: " + i.get_description() + ", Created on: " + str(i.get_date()))
                    for i in snapshots:
                        try:
                            while True:
                                try:
                                    if not config.get_dry_run():
                                        i.delete()
                                    Logger.log("Snapshot deletion started ...")
                                    VMTools.wait_for_snapshot_operation(vm, config, "deletion")
                                    done = True
                                    break
                                except Exception as e:
                                    if "status: 409" in str(e):
                                        if config.get_debug():
                                            Logger.log("Got 409 wait for operation to be finished, DEBUG: " + str(e))
                                        time.sleep(config.get_timeout())
                                        continue
                                    else:
                                        Logger.log("  !!! Found another exception for VM: " + vm_name)
                                        Logger.log("  DEBUG: " + str(e))
                                        sys.exit(1)
                        except Exception as e:
                            Logger.log("  !!! Can't delete snapshot for VM: " + vm_name)
                            Logger.log("  Description: " + i.get_description() + ", Created on: " + str(i.get_date()))
                            Logger.log("  DEBUG: " + str(e))
                            sys.exit(1)
            if done:
                Logger.log("Snapshots deleted")
                            
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
            for i in api.vms.list():
                i_vm_name = str(i.get_name())
                if i_vm_name.startswith(vm_name + config.get_vm_middle()):
                    Logger.log("Delete cloned VM started ...")
                    if not config.get_dry_run():
                        vm = api.vms.get(i_vm_name)
                        vm.delete_protected = False
                        vm = vm.update()
                        vm.delete()
                        while i_vm_name in [vm.name for vm in api.vms.list()]:
                            if config.get_debug():
                                Logger.log("Deletion of cloned VM in progress ...")
                            time.sleep(config.get_timeout())
                        done = True
        except Exception as e:
            Logger.log("!!! Can't delete cloned VM (" + i_vm_name + ")")
            raise e
        if done:
            Logger.log("Cloned VM deleted")

    @staticmethod
    def wait_for_vm_operation(api, config, comment, vm_name):
        """
        Wait for a vm operation to be finished
        :param vm: Virtual machine object
        :param config: Configuration
        :param comment: This comment will be used for debugging output
        """
        while str(api.vms.get(vm_name + config.get_vm_middle() + config.get_vm_suffix()).get_status().state) != 'down':
            if config.get_debug():
                Logger.log(comment + " in progress ...")
            time.sleep(config.get_timeout())

    @staticmethod
    def delete_old_backups(api, config, vm_name):
        """
        Delete old backups from the export domain
        :param api: ovirtsdk api
        :param config: Configuration
        """
        exported_vms = api.storagedomains.get(config.get_export_domain()).vms.list()
        for i in exported_vms:
            vm_name_export = str(i.get_name())
            if vm_name_export.startswith(vm_name + config.get_vm_middle()):
                datetimeStart = datetime.datetime.combine((datetime.date.today() - datetime.timedelta(config.get_backup_keep_count())), datetime.datetime.min.time())
                timestampStart = time.mktime(datetimeStart.timetuple())
                datetimeCreation = i.get_creation_time()
                datetimeCreation = datetimeCreation.replace(hour=0, minute=0, second=0)
                timestampCreation = time.mktime(datetimeCreation.timetuple())
                if timestampCreation < timestampStart:
                    Logger.log("Backup deletion started for backup: " + vm_name_export)
                    if not config.get_dry_run():
                        i.delete()
                        while vm_name_export in [vm.name for vm in api.storagedomains.get(config.get_export_domain()).vms.list()]:
                            if config.get_debug():
                                Logger.log("Delete old backup in progress ...")
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
            vm_size += disk.size
        storage_space_threshold = 0
        if config.get_storage_space_threshold() > 0:
            storage_space_threshold = config.get_storage_space_threshold()
        vm_size *= (1 + storage_space_threshold)
        if (sd.available - vm_size) <= 0:
            raise Exception("!!! The is not enough free storage on the storage domain '" + config.get_storage_domain() + "' available to backup the VM '" + vm.name + "'")
