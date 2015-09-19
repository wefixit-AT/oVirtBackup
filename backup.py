#!/usr/bin/python
import ovirtsdk.api
from ovirtsdk.xml import params
import sys
import time
from vmtools import VMTools
from config import Config
from getopt import getopt, GetoptError

"""
Main class to make the backups
"""

def main(argv):
    usage = "backup.py -c <config.cfg>"
    try:
        opts, args = getopt(argv, "hc:d")
        debug = False
        if not opts:
            print usage
            sys.exit(1)
        for opt, arg in opts:
            if (opt == "-h") or (opt == "--help"):
                print usage
                sys.exit(0)
            elif opt in ("-c"):
                config_file = arg
            elif opt in ("-d"):
                debug = True
    except GetoptError:
        print usage
        sys.exit(1)
        
    config = Config(config_file, debug)
    
    time_start = int(time.time())
    
    # Connect to server
    api = ovirtsdk.api.API(
        url=config.get_server(),
        username=config.get_username(),
        password=config.get_password(),
        insecure=True,
        debug=False
    )
    
    # Test if all VM names are valid
    # print "found "+str(len(vm_from_list))+" vm's"
    for vm_from_list in config.get_vm_names():
        if not api.vms.get(vm_from_list):
            print "!!! There are no VM with the following name in your cluster: " + vm_from_list
            sys.exit(1)
    
    for vm_from_list in config.get_vm_names():
    
        # Get the VM
        vm = api.vms.get(vm_from_list)
        
        # Cleanup: Delete the cloned VM
        VMTools.delete_vm(api, config, vm_from_list)
        
        # Delete old backup snapshots
        VMTools.delete_snapshots(vm, config, vm_from_list)
        
        # Create a VM snapshot:
        try:
            print "Snapshot creation started ..."
            if not config.get_dry_run():
                vm.snapshots.add(params.Snapshot(description=config.get_snapshot_description(), vm=vm))
                VMTools.wait_for_snapshot_operation(vm, config, "creation")
            print "Snapshot created"
        except Exception as e:
            print "Can't create snapshot for VM: " + vm_from_list
            print "config.debug: " + str(e)
            sys.exit(1)
        
        # Clone the snapshot into a VM
        snapshots = vm.snapshots.list(description=config.get_snapshot_description())
        if not snapshots:
            print "!!! No snapshot found"
            sys.exit(1)
        snapshot_param = params.Snapshot(id=snapshots[0].id)
        snapshots_param = params.Snapshots(snapshot=[snapshot_param])
        print "Clone into VM started ..."
        if not config.get_dry_run():
            api.vms.add(params.VM(name=vm_from_list + config.get_vm_middle() + config.get_vm_suffix(), memory=vm.get_memory(), cluster=api.clusters.get(config.get_cluster_name()), snapshots=snapshots_param))    
            VMTools.wait_for_vm_operation(api, config, "Cloning", vm_from_list)
        print "Cloning finished"
        
        # Delete backup snapshots
        VMTools.delete_snapshots(vm, config, vm_from_list)
        
        # Delete old backups
        VMTools.delete_old_backups(api, config, vm_from_list)
        
        # Export the VM
        try:
            vm_clone = api.vms.get(vm_from_list + config.get_vm_middle() + config.get_vm_suffix())
            print "Export started ..."
            if not config.get_dry_run():
                vm_clone.export(params.Action(storage_domain=api.storagedomains.get(config.get_export_domain())))
                VMTools.wait_for_vm_operation(api, config, "Exporting")
            print "Exporting finished"
        except Exception as e:
            print "Can't export cloned VM (" + vm_from_list + config.get_vm_middle() + config.get_vm_suffix() + ") to domain: " + config.get_export_domain()
            print "config.debug: " + str(e)
            sys.exit(1)
            
        # Delete the VM
        VMTools.delete_vm(api, config, vm_from_list)
        
        time_end = int(time.time())
        time_diff = (time_end - time_start)
        time_minutes = int(time_diff / 60)
        time_seconds = time_diff % 60
        
        # Disconnect from the server
        api.disconnect()
        
        print "Duration: " + str(time_minutes) + ":" + str(time_seconds) + " minutes"
        print "VM exported as " + vm_from_list + config.get_vm_middle() + config.get_vm_suffix()
        print "Backup done for: " + vm_from_list
    print "All backups done"

if __name__ == "__main__":
   main(sys.argv[1:])
