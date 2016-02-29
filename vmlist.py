#! /usr/bin/python

import sys
import os
import re
import time
#import logging
from logger import Logger

#Configure
 
#LOGconfig_file="list_setup.log"

#logging.basicConfig(level=logging.DEBUG,
#                    format='%(asctime)s %(levelname)s %(message)s',
#                    filename=LOGconfig_file,
#                    filemode='w')
def get_vm_list (vms,config_file):
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
#               logging.debug('Unexpected error getting list of vms: %s' % ex)
		Logger.log('Unexpected error getting list of vms: %s' % ex)
