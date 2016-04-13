import ConfigParser
from ConfigParser import NoSectionError, NoOptionError
import sys
import json
from time import strftime

class Config(object):
    """
    Class to read the config from the config file and serve these config
    """
    def __init__(self, config_file, debug):
        try:
            config_parser = ConfigParser.RawConfigParser()
            config_parser.read(config_file)
            section = "config"
            self.__vm_names = json.loads(config_parser.get(section, "vm_names"))
            self.__vm_middle = config_parser.get(section, "vm_middle")
            self.__vm_suffix = "_"
            self.clear_vm_suffix
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
            self.__vm_name_max_length = config_parser.getint(section, "vm_name_max_length")
            self.__use_short_suffix = config_parser.getboolean(section, "use_short_suffix")
            self.__storage_domain = config_parser.get(section, "storage_domain")
            self.__storage_space_threshold = config_parser.getfloat(section, "storage_space_threshold")
        except NoSectionError as e:
            print str(e)
            sys.exit(1)
        except NoOptionError as e:
            print str(e)
            sys.exit(1)

    def get_vm_names(self):
        return self.__vm_names
    
    def get_vm_middle(self):
        return self.__vm_middle


    def clear_vm_suffix(self):
        self.__vm_suffix = "_" + strftime("%Y%m%d_%H%M%S")
        if self.__use_short_suffix:
            self.__vm_suffix = "_" + strftime("%m%d%S")


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


    def get_vm_name_max_length(self):
        return self.__vm_name_max_length


    def get_use_short_suffix(self):
        return self.__use_short_suffix


    def get_storage_domain(self):
        return self.__storage_domain


    def get_storage_space_threshold(self):
        return self.__storage_space_threshold
