import time
import ConfigParser
from ConfigParser import NoSectionError, NoOptionError
import sys

class Config(object):
    """
    Class to read the config from the config file and serve these config
    """
    def __init__(self, config_file, debug):
        try:
            config_parser = ConfigParser.RawConfigParser()
            config_parser.read(config_file)
            section = "config"
            self.__vm_name = config_parser.get(section, "vm_name")
            self.__vm_middle = config_parser.get(section, "vm_middle")
            self.__vm_suffix = "_" + str(int(time.time()))
            self.__server = config_parser.get(section, "server")
            self.__username = config_parser.get(section, "username")
            self.__password = config_parser.get(section, "password")
            self.__snapshot_description = config_parser.get(section, "snapshot_description")
            self.__cluster_name = config_parser.get(section, "cluster_name")
            self.__export_domain = config_parser.get(section, "export_domain")
            self.__timeout = config_parser.getint(section, "timeout")
            self.__backup_keep_count = config_parser.getint(section, "backup_keep_count")
            self.__dry_run = config_parser.getboolean(section, "dry_run")
            self.__debug = debug
        except NoSectionError as e:
            print str(e)
            sys.exit(1)
        except NoOptionError as e:
            print str(e)
            sys.exit(1)

    def get_vm_name(self):
        return self.__vm_name
    
    def get_vm_middle(self):
        return self.__vm_middle


    def get_vm_suffix(self):
        return self.__vm_suffix


    def get_server(self):
        return self.__server


    def get_username(self):
        return self.__username


    def get_password(self):
        return self.__password


    def get_snapshot_description(self):
        return self.__snapshot_description


    def get_cluster_name(self):
        return self.__cluster_name


    def get_export_domain(self):
        return self.__export_domain


    def get_timeout(self):
        return self.__timeout


    def get_backup_keep_count(self):
        return self.__backup_keep_count


    def get_dry_run(self):
        return self.__dry_run


    def get_debug(self):
        return self.__debug
