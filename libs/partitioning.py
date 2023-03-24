from sh import e2label, lsblk, mount, umount
import re
import json

lsblk_unk_column = re.compile(r"lsblk: unknown column: (?P<column>.*)")
lsblk_unk_device = re.compile(r"lsblk: (?P<device>.*): not a block device")
COLUMNS=["size", "rm", "partuuid", "uuid", "fstype", "partlabel", "label", "mountpoint"]


class LsblkHelper:
    def call(columns=["size", "partuuid", "uuid", "fstype", "partlabel", "label"], device=None):
        if "path" not in columns:
            columns.append("path")

        if "type" not in columns:
            columns.append("type")

        args = ["-o", f"{','.join(columns)}", "-J", "-b", "-p", "-n"]
        if device != None:
            args.append(device)

        try:
            output = lsblk(args)
        except Exception as ex:
            # Find errors
            match = lsblk_unk_column.match(output)
            if match:
                print(output)
                raise ValueError(f"Unknown column: {match['column']}")

            match = lsblk_unk_device.match(output)
            if match:
                raise ValueError(f"Unknown device: {match['device']}")
            
            raise ex

        output = json.loads(output)
        if "blockdevices" not in output:
            raise Exception("Unknown lsblk error")

        return output["blockdevices"]

class Disk:
    def __init__(self, path, size, removable, partitions):
        self.path = path
        self.size = size
        self.removable = removable
        self.partitions = partitions

    def from_device(path):
        disk = None
        devices = LsblkHelper.call(COLUMNS, path)
        parts = []

        # Find disk
        for device in devices:
            if device["path"] != path:
                continue

            if device["type"] != "disk":
                raise ValueError(f"Not a disk: {path}")

            disk = device

        if disk is None:
            raise Exception("Could not find device info")

        # Find children
        for device in devices:
            if not device["path"].startswith(disk["path"]):
                continue

            if device["type"] != "part":
                continue

            parts.append(device)

        disk["children"] = parts
        return Disk.from_object(devices)
    
    def from_object(device):
        path = device["path"]
        size = device["size"]
        removable = device["rm"]
        parts = []

        for part in device["children"]:
            parts.append(Partition.from_object(part))

        return Disk(path, size, removable, parts)
    
    def get_all():
        disks = {}
        devices = LsblkHelper.call(COLUMNS)
        for disk in devices:
            if disk["type"] != "disk":
                continue

            parts = []
            for part in devices:
                if not part["path"].startswith(disk["path"]):
                    continue

                if part["type"] != "part":
                    continue

                parts.append(part)

            disk["children"] = parts
            disks[disk["path"]] = Disk.from_object(disk)

        return disks
        

class Partition:
    def __init__(self, path, size, removable, partuuid, fsuuid, fstype, partlabel, fslabel, mountpoint):
        self.path = path
        self.size = size
        self.removable = removable
        self.partuuid = partuuid
        self.fsuuid = fsuuid
        self.fstype = fstype
        self.partlabel = partlabel
        self.fslabel = fslabel
        self.mountpoint = mountpoint

    def from_device(path):
        devices = LsblkHelper.call(COLUMNS, path)
        for device in devices:
            if device["path"] != path:
                continue

            if device["type"] != "part":
                raise ValueError(f"Not a partition: {path}")

            return Partition.from_object(device)

        raise Exception("Could not find device info")

    def from_object(device):
        path = device["path"]
        size = device["size"]
        removable = device["rm"]
        partuuid = device["partuuid"]
        fsuuid = device["uuid"]
        fstype = device["fstype"]
        partlabel = device["partlabel"]
        fslabel = device["label"]
        mountpoint = device["mountpoint"]
        return Partition(path, size, removable, partuuid, fsuuid, fstype, partlabel, fslabel, mountpoint)

    def get_all():
        partitions = {}
        devices = LsblkHelper.call(COLUMNS)
        for device in devices:
            if device["type"] != "part":
                continue

            partitions[device["path"]] = Partition.from_object(device)

        return partitions
    
    def set_fslabel(self, label):
        if label is None:
            label = ""

        e2label(self.path, label)

    def mount(self, mountpoint):
        mount(self.path, mountpoint)
        self.mountpoint = mountpoint

    def umount(self, force=False):
        if not self.mountpoint and not force:
            return

        if force:
            umount("--force", self.path)
        else:
            umount(self.path)

        self.mountpoint = None