#! /usr/bin/python

import sys
import os
import re
from ovirtsdk.api import API 
from ovirtsdk.xml import params
from threading import Thread
import time
import logging

#Configure
 
APIURL="https://engine.example.com/api/"
APIUSER="admin@internal"
APIPASS="securepassword:)"
CAFILE="ca.crt"
FILENAME="config.cfg"
LOGFILENAME="list_setup.log"

s1= '.'

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename=LOGFILENAME,
                    filemode='w')
def getObjInfo (objlist):
	vmstring="vm_names: ["
	for obj in objlist[:-1]:
		vmstring += '"'+obj.name+'"'+", " 
	vmstring +='"'+objlist[-1].name+'"'+"]"
	#print vmstring 
	with open(FILENAME) as myfile:
		out=open("config.tmp","w")
		for line in myfile:
			out.write(re.sub("^vm_names.*$", vmstring, line))
		out.close()
		os.rename("config.tmp", FILENAME)
if __name__ == "__main__":
   	try:	
        	api = API(url=APIURL,
                      username=APIUSER,
              	      password=APIPASS,
                      ca_file=CAFILE)
    		try: 
			print ' \n I am logging in %s \n' % LOGFILENAME

			getObjInfo(api.vms.list(max=400))

    		except Exception as e:
        		logging.debug('Error:\n%s' % str(e))
		
    		api.disconnect()
	
	except Exception as ex:
   		logging.debug('Unexpected error: %s' % ex)
