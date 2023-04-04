"""Utility Classes for partitioning on linux"""
from __future__ import annotations
import os.path as path
import typing
import json
import re
from .constants import LSBLK_DEFAULT_COLUMNS
from sh import e2label, lsblk, mount, umount, mkdir

lsblk_unk_column = re.compile(r"lsblk: unknown column: (?P<column>.*)")
lsblk_unk_device = re.compile(r"lsblk: (?P<device>.*): not a block device")

class LsblkHelper:
    """lsblk Helper class"""
    @staticmethod
    def call(columns: "typing.Optional[list[str]]"=None, device=None):
        """calls lsblk with given arguments"""

        if not columns:
            columns = ["size", "partuuid", "uuid",
                       "fstype", "partlabel", "label"]
        if "path" not in columns:
            columns.append("path")

        if "type" not in columns:
            columns.append("type")

        args = ["-o", f"{','.join(columns)}", "-J", "-b", "-p", "-n"]
        if device is not None:
            args.append(device)
        output = ""
        try:
            output = lsblk(args)
        except Exception as ex:
            # Find errors
            match = lsblk_unk_column.match(output)
            if match:
                print(output)
                raise ValueError(f"Unknown column: {match['column']}") from ex

            match = lsblk_unk_device.match(output)
            if match:
                raise ValueError(f"Unknown device: {match['device']}") from ex

            raise ex

        output = json.loads(output)
        if "blockdevices" not in output:
            raise SystemError("Unknown lsblk error")

        return output["blockdevices"]


class Disk:
    """Disk management utility class"""
    def __init__(self, _path, size, removable, partitions):
        self.path: str = _path
        self.size: int = size
        self.removable: bool = removable
        self.partitions: list[Partition] = partitions

    @staticmethod
    def from_device(_path) -> Disk:
        """creates disk object from drive path"""
        disk = None
        devices = LsblkHelper.call(LSBLK_DEFAULT_COLUMNS, _path)
        parts = []

        # Find disk
        for device in devices:
            if device["path"] != _path:
                continue

            if device["type"] != "disk":
                raise ValueError(f"Not a disk: {_path}")

            disk = device

        if disk is None:
            raise FileNotFoundError("Could not find device info")

        # Find children
        for device in devices:
            if not device["path"].startswith(disk["path"]):
                continue

            if device["type"] != "part":
                continue

            parts.append(device)

        disk["children"] = parts
        return Disk.from_object(devices)

    @staticmethod
    def from_object(device: dict[str, str]) -> Disk:
        """creates disk from dictionary"""
        _path = device["path"]
        size = device["size"]
        removable = device["rm"]
        parts = []

        for part in device["children"]:
            parts.append(Partition.from_object(part))

        return Disk(_path, size, removable, parts)

    @staticmethod
    def get_all() -> dict[str, Disk]:
        """returns all Drives"""
        disks = {}
        devices = LsblkHelper.call(LSBLK_DEFAULT_COLUMNS)
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
    """Partition utility class"""
    def __init__(self, _path, size, removable,
                  partuuid, fsuuid, fstype, partlabel, fslabel, mountpoint):
        self.path: str = _path
        self.size: int = size
        self.removable: bool = removable
        self.partuuid: str = partuuid
        self.fsuuid: str = fsuuid
        self.fstype: str = fstype
        self.partlabel: str = partlabel
        self.fslabel: str = fslabel
        self.mountpoint: str = mountpoint
    @classmethod
    def from_device(cls, _path: str) -> Partition:
        """create partition from systems partition path"""
        devices = LsblkHelper.call(LSBLK_DEFAULT_COLUMNS, _path)
        for device in devices:
            if device["path"] != _path:
                continue

            if device["type"] != "part":
                raise ValueError(f"Not a partition: {_path}")

            return cls.from_object(device)

        raise FileNotFoundError("Could not find device info")

    @classmethod
    def from_object(cls, device: "dict[str, str]") -> Partition:
        """creates partition from dictionary"""
        _path = device["path"]
        size = device["size"]
        removable = device["rm"]
        partuuid = device["partuuid"]
        fsuuid = device["uuid"]
        fstype = device["fstype"]
        partlabel = device["partlabel"]
        fslabel = device["label"]
        mountpoint = device["mountpoint"]
        return cls(_path, size, removable, partuuid, fsuuid, fstype,
                         partlabel, fslabel, mountpoint)

    @staticmethod
    def get_all() -> dict[str, Partition]:
        """returns all available partitions"""
        partitions = {}
        devices = LsblkHelper.call(LSBLK_DEFAULT_COLUMNS)
        for device in devices:
            if device["type"] != "part":
                continue

            partitions[device["path"]] = Partition.from_object(device)

        return partitions

    def set_fslabel(self, label: str):
        """sets label on partition"""
        if label is None:
            label = ""

        e2label(self.path, label)

    def mount(self, mountpoint: str, create_mountpoint=True):
        """mount partition to system"""
        if not path.isdir(mountpoint):
            if create_mountpoint:
                mkdir("-p", mountpoint)
            else:
                raise FileNotFoundError("Mountpoint does not exist.")

        mount(self.path, mountpoint)
        self.mountpoint = mountpoint

    def umount(self, force=False):
        """unmounts partition from system"""
        if not self.mountpoint and not force:
            return

        if force:
            umount("--force", self.path)
        else:
            umount(self.path)

        self.mountpoint = None