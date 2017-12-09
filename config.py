from ConfigParser import (
    RawConfigParser,
    NoSectionError,
    NoOptionError,
)
import re
import sys
import json
from time import strftime


CONFIG_SECTION = "config"
DEFAULTS = {
    "logger_fmt": "%(asctime)s: %(message)s",
    "logger_file_path": None,
    "persist_memorystate": "false",
}


class Config(object):
    """
    Class to read the config from the config file and serve these config
    """
    def __init__(self, fd, debug, arguments):
        try:
            self._cp = config_parser = RawConfigParser(defaults=DEFAULTS)
            config_parser.readfp(fd)

            section = CONFIG_SECTION
            # Update with options passed from CLI interface
            for key, val in arguments.items():
                if val is not None:
                    config_parser.set(section, key, str(val))

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
            self.__backup_keep_count = config_parser.get(section, "backup_keep_count")
            self.__backup_keep_count_by_number = config_parser.get(section, "backup_keep_count_by_number")
            self.__dry_run = config_parser.getboolean(section, "dry_run")
            self.__debug = debug
            self.__vm_name_max_length = config_parser.getint(section, "vm_name_max_length")
            self.__use_short_suffix = config_parser.getboolean(section, "use_short_suffix")
            self.__storage_domain = config_parser.get(section, "storage_domain")
            self.__storage_space_threshold = config_parser.getfloat(section, "storage_space_threshold")
            self.__logger_fmt = config_parser.get(section, "logger_fmt")
            self.__logger_file_path = config_parser.get(section, "logger_file_path")
            self.__persist_memorystate = config_parser.getboolean(section, "persist_memorystate")
        except (NoSectionError, NoOptionError) as e:
            print str(e)
            sys.exit(1)

    def get_vm_names(self):
        return self.__vm_names

    def set_vm_names(self, vms):
        self._cp.set(
            CONFIG_SECTION, 'vm_names', json.dumps(vms)
        )
        self.__vm_names = vms[:]

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
        if self.__backup_keep_count:
            self.__backup_keep_count = int(self.__backup_keep_count)
        return self.__backup_keep_count


    def get_backup_keep_count_by_number(self):
        if self.__backup_keep_count_by_number:
            self.__backup_keep_count_by_number = int(self.__backup_keep_count_by_number)
        return self.__backup_keep_count_by_number


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


    def get_logger_fmt(self):
        return self.__logger_fmt

    def get_logger_file_path(self):
        return self.__logger_file_path

    def get_persist_memorystate(self):
        return self.__persist_memorystate

    def write_update(self, filename):
        """
        This method takes name of config file and update it according
        to updated fields.

        This method doesn't want to wipe out commnents from config file.

        The filename must exist.
        """
        # self._cp.write(fd)  # This call wipes out all comments ...
        changeable_fields = ('vm_names',)
        with open(filename) as fh:
            content = fh.readlines()
        for field in changeable_fields:
            pattern = "^%s *[:=].*$" % field
            value = "%s = %s\n" % (field, self._cp.get(CONFIG_SECTION, field))
            content = [re.sub(pattern, value, line) for line in content]
        with open(filename, 'w') as fh:
            fh.write("".join(content))
