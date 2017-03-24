from cStringIO import StringIO
from config import Config


default_config_data = [
    "[config]",
    "vm_names=[\"vm1\", \"vm2\"]",
    "vm_middle=_BACKUP",
    "snapshot_description=Snapshot for backup script",
    "server=https://my-ovirt/ovirt-engine/api/",
    "username=admin@internal",
    "password=secret",
    "export_domain=backup",
    "timeout=5",
    "cluster_name=Default",
    "backup_keep_count=3",
    "dry_run=False",
    "vm_name_max_length=32",
    "use_short_suffix=False",
    "storage_domain=storage",
    "storage_space_threshold=0.1",
    "logger_fmt=%(asctime)s: %(message)s",
    "logger_file_path=",
]


def test_config_overwitten_from_cli():
    #
    data_stream = StringIO("\n".join(default_config_data))
    cli_arguments = {
        "password": "newsecret",
        "username": "newadmin@internal",
        "cluster_name": None,
    }
    c = Config(data_stream, False, cli_arguments)
    assert c.get_password() == "newsecret"
    assert c.get_username() == "newadmin@internal"
    assert c.get_cluster_name() == "Default"


def test_config_rewrite_vm_names(tmpdir):
    new_vms = ["new_vm1", "new_vm2"]
    p = tmpdir.join("config.cfg")
    p.write("\n".join(default_config_data))
    with p.open() as fh:
        c = Config(fh, False, dict())
    assert p.check()
    c.set_vm_names(new_vms)
    assert c.get_vm_names() == new_vms
    c.write_update(str(p))
    data = p.read()
    assert 'vm_names = ["new_vm1", "new_vm2"]' in data
    with p.open() as fh:
        c = Config(fh, False, dict())
    assert c.get_vm_names() == new_vms


def test_config_persist_memory():
    # Test default
    data_stream = StringIO("\n".join(default_config_data))
    c = Config(data_stream, False, dict())
    assert c.get_persist_memorystate() is False
    # Test setting from config file
    data_stream = StringIO(
        "\n".join(
            default_config_data + ['persist_memorystate=True']
        )
    )
    c = Config(data_stream, False, dict())
    assert c.get_persist_memorystate() is True
    # Test setting from CLI
    data_stream = StringIO("\n".join(default_config_data))
    c = Config(data_stream, False, {"persist_memorystate": True})
    assert c.get_persist_memorystate() is True
