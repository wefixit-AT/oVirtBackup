import logging
import time
import sys
import datetime
import operator
import re

logger = logging.getLogger()
import ovirtsdk4.types as types


class VMTools:
    """
    Class which holds static methods which are used more than once
    """

    @staticmethod
    def wait_for_snapshot_operation(api, vm, config, comment):
        """
        Wait for a snapshot operation to be finished
        :param vm: Virtual machine object
        :param config: Configuration
        :param comment: This comment will be used for debugging output
        """
        vm_service = api.system_service().vms_service().vm_service(vm.id)
        snaps_service = vm_service.snapshots_service()
        snapshots = snaps_service.list()
        for i in snapshots:
            if i.description == config.get_snapshot_description():
                snap_service = snaps_service.snapshot_service(i.id)
                while True:
                    try:
                        snap = snap_service.get()
                    except:
                        break
                    if snap.snapshot_status == types.SnapshotStatus.OK:
                        break
                    logger.debug("Snapshot operation(%s) in progress ...", comment)
                    logger.debug("Snapshot id=%s status=%s", snap.id , snap.snapshot_status)
                    time.sleep(config.get_timeout())


    @staticmethod
    def delete_snapshots(api, vm, config, vm_name):
        """
        Deletes a backup snapshot
        :param vm: Virtual machine object
        :param config: Configuration
        """
        logger.debug("Search backup snapshots matching Description=\"%s\"", config.get_snapshot_description())
        vm_service = api.system_service().vms_service().vm_service(vm.id)
        snaps_service = vm_service.snapshots_service()
        snapshots = snaps_service.list()
        done = False
        if snapshots:
            for i in snapshots:
                if i.description == config.get_snapshot_description():
                    logger.debug("Found backup snapshot to delete. Description: %s, Created on: %s", i.description, i.date)
                    try:
                        while True:
                            try:
                                if not config.get_dry_run():
                                    snaps_service.snapshot_service(i.id).remove()
                                    logger.info("Snapshot deletion started ...")
                                    VMTools.wait_for_snapshot_operation(api, vm, config, "deletion")
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
        done = False
        try:
            vms_service = api.system_service().vms_service()
            vm_search_regexp = ("name=%s%s__*" % (vm_name, config.get_vm_middle()))
            for vm in vms_service.list(search=vm_search_regexp):
                logger.info("Delete cloned VM (%s) started ..." % vm.name)
                if not config.get_dry_run():
                    vm_service = vms_service.vm_service(vm.id)
                    if vm_service is None:
                        logger.warn(
                            "The VM (%s) doesn't exist anymore, "
                            "skipping deletion ...", vm.name
                        )
                        done = True
                        continue
                    vm.delete_protected = False
                    vm_service.update(vm)
                    while True:
                        try:
                            vm_service.remove()
                            break
                        except:
                            logger.debug("Wait for previous clone operation to complete (VM %s status is %s)..." , vm.name, vm.status)
                            time.sleep(config.get_timeout())
                    while True:
                        try:
                            vm_service.get()
                        except:
                            break
                        logger.debug("Deletion of cloned VM (%s) in progress ..." % vm.name)
                        time.sleep(config.get_timeout())
                    done = True
        except Exception as e:
            logger.info("!!! Can't delete cloned VM (%s)", vm.name)
            raise e
        if done:
            logger.info("Cloned VM (%s) deleted" , vm.name)

    @staticmethod
    def wait_for_vm_operation(api, config, comment, vm_name):
        """
        Wait for a vm operation to be finished
        :param vm: Virtual machine object
        :param config: Configuration
        :param comment: This comment will be used for debugging output
        """
        #not used 
        composed_vm_name = "%s%s%s" % (
            vm_name, config.get_vm_middle(), config.get_vm_suffix()
        )
        while True:
            vm = api.system_service().vms_service().list(search='name=%s' % composed_vm_name)
            if len(vm) == 0 :
                logger.warn(
                    "The VM (%s) doesn't exist anymore, "
                    "leaving waiting loop ...", composed_vm_name
                )
                break

            vm = vm[0]
            if vm.status == types.VmStatus.DOWN:
                break
            logger.debug(
                "%s in progress (VM %s status is '%s') ...",
                comment, composed_vm_name, vm.status,
            )
            time.sleep(config.get_timeout())

    @staticmethod
    def delete_old_backups(api, config, vm_name):
        """
        Delete old backups from the export domain
        :param api: ovirtsdk api
        :param config: Configuration
        """
        vm_search_regexp = r'^'+ vm_name + config.get_vm_middle() + '*'
        logger.debug("Looking for old backup to delete matching %s and older than %s days...", vm_search_regexp, config.get_backup_keep_count())
        sds_service = api.system_service().storage_domains_service()
        export_sd = sds_service.list(search='name=%s' % config.get_export_domain() )[0]
        vms_service = sds_service.storage_domain_service(export_sd.id).vms_service()
        #missing list(search'name=... on storage_domain_service().vms_service().list()
        exported_vms = vms_service.list()
        exported_vms = [i for i in exported_vms if re.match(vm_search_regexp,i.name) ]
        #not really needed to sort 
        logger.info("Found %s old backup images in export_domain.", len(exported_vms))
        exported_vms.sort(key=lambda x: x.creation_time)
        for i in exported_vms:
            datetimeStart = datetime.datetime.combine((datetime.date.today() - datetime.timedelta(config.get_backup_keep_count())), datetime.datetime.min.time())
            timestampStart = time.mktime(datetimeStart.timetuple())
            datetimeCreation = i.creation_time
            datetimeCreation = datetimeCreation.replace(hour=0, minute=0, second=0)
            timestampCreation = time.mktime(datetimeCreation.timetuple())
            if timestampCreation < timestampStart:
                logger.info("Backup deletion (by date) started for backup: %s", i.name)
                if not config.get_dry_run():
                    vms_service.vm_service(id = i.id).remove()
                    while True:
                        try:
                            vms_service.vm_service(id = i.id).get()
                            logger.debug("Delete old backup (%s) in progress ..." , i.name)
                            time.sleep(config.get_timeout())
                        except: 
                            logger.info("Backup deletion complete for backup: %s", i.name)
                            break

    @staticmethod
    def delete_old_backups_by_number(api, config, vm_name):
        """
        Delete old backups from the export domain by number of requested
        :param api: ovirtsdk api
        :param config: Configuration
        """
        vm_search_regexp = r'^'+ vm_name + config.get_vm_middle() + '*'
        logger.debug("Looking for old backup to delete matching %s, keeping max %s images...", vm_search_regexp, config.get_backup_keep_count_by_number())
        sds_service = api.system_service().storage_domains_service()
        export_sd = sds_service.list(search='name=%s' % config.get_export_domain() )[0]
        vms_service = sds_service.storage_domain_service(export_sd.id).vms_service()
        #missing list(search'name=... on storage_domain_service().vms_service().list()
        exported_vms = vms_service.list()
        exported_vms = [i for i in exported_vms if re.match(vm_search_regexp,i.name) ]
        exported_vms.sort( key = lambda x: x.creation_time)
        logger.info("Found %s old backup images in export_domain.", len(exported_vms))
        while len(exported_vms) > config.get_backup_keep_count_by_number():
            i = exported_vms.pop(0)
            logger.info("Backup deletion (by number) started for backup: %s", i.name)
            if not config.get_dry_run():
                vms_service.vm_service(id = i.id).remove()
                while True:
                    try:
                        vms_service.vm_service(id = i.id).get()
                        logger.debug("Delete old backup (%s) in progress ..." , i.name)
                        time.sleep(config.get_timeout())
                    except: 
                        logger.info("Backup deletion complete for backup: %s", i.name)
                        break

    @staticmethod
    def check_free_space(api, config, vm):
        """
        Check if the summarized size of all VM disks is available on the storagedomain
        to avoid running out of space
        """
        sd =  api.system_service().storage_domains_service().list(search='name=%s' % config.get_storage_domain())[0]
        vm_service = api.system_service().vms_service().vm_service(vm.id)
        disk_attachments = vm_service.disk_attachments_service().list()
        vm_size = 0
        for disk_attachment in disk_attachments:
            disk_id = disk_attachment.disk.id
            disk = api.system_service().disks_service().disk_service(disk_id).get()
            # For safety reason "vm.actual_size" is not used
            if disk.provisioned_size is not None:
                vm_size += disk.provisioned_size
        storage_space_threshold = 0
        if config.get_storage_space_threshold() > 0:
            storage_space_threshold = config.get_storage_space_threshold()
        vm_size *= (1 + storage_space_threshold)
        if (sd.available - vm_size) <= 0:
            raise Exception("!!! The is not enough free storage on the storage domain '%s' available to backup the VM '%s'" % (config.get_storage_domain(), vm.name))

    @staticmethod
    def check_storage_domain_status(api, data_center, storage_domain):
        """
        Check the state of the export domain
        :param api: ovirt api module
        :param data_center: data center name where the storage domain attached
        :param storage_domain: storage domain name
        :return: True if 'active'
        :raises: Exception if storage domain is not 'active'
        """
        dcs_service = api.system_service().data_centers_service()
        dc = dcs_service.list(search='name=%s' % data_center)[0]
        dc_service = dcs_service.data_center_service(dc.id)
        sds_service = dc_service.storage_domains_service()
        sd = sds_service.list(search='name=%s' % storage_domain)[0]

        info_msg = (
            "The storage domain {0} is in state {1}".format(
                storage_domain, sd.status
            )
        )
        if sd.status == types.StorageDomainStatus.ACTIVE:
            logger.info(info_msg)
            return True

        raise Exception(info_msg)
