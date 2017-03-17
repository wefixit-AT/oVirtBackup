#! /usr/bin/python

import os
import re
import logging

logger = logging.getLogger()

def get_vm_list(vms, config_file):
	try:
		vmstring="vm_names: ["
		for vm in vms[:-1]:
			vmstring += '"'+vm.name+'"'+", "
		vmstring +='"'+vms[-1].name+'"'+"]"
		#print vmstring
		with open(config_file) as myfile:
			out=open("/tmp/config.tmp","w")
			for line in myfile:
				out.write(re.sub("^vm_names.*$", vmstring, line))
			out.close()
			os.rename("/tmp/config.tmp", config_file)
	except Exception as ex:
		logger.debug('Unexpected error getting list of vms: %s', ex)
