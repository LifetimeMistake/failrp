import os, sys
from os.path import exists, join, isfile
from os import listdir
import jc
import re

STATIC_FILES = [
    "Info-OS-prober.txt",
    "Info-dmi.txt",
    "Info-img-id.txt",
    "Info-img-size.txt",
    "Info-lshw.txt",
    "Info-lspci.txt",
    "Info-packages.txt",
    "Info-saved-by-cmd.txt",
    "Info-smart.txt",
    "blkdev.list",
    "blkid.list",
    "clonezilla-img",
    "dev-fs.list",
    "efi-nvram.dat",
    "parts"
]

DYNAMIC_FILES = {
    "drive": r'^([a-zA-Z0-9_-]+)-([a-zA-Z0-9_-]+)(\.([a-zA-Z0-9_-]+))?$',   # drive match regex
    "partition": r'^([\w-]+)-([\w-]+)\.([\w-]+)$'                           # partition match regex
}

class Validator():
    def __init__(self, img: str):
        self.path = img

    def check_static(self):
        for file in STATIC_FILES:
            if not isfile():
                raise FileNotFoundError(f"File {file} does not exist!")

    def list_drives(self):
        with open(self.this_repo("blkdev.list"), encoding="utf-8") as f:
            parsed_lsblk = jc.parse("lsblk",f.read())
            for dev in parsed_lsblk:
                if dev["type"] == "disk":
                    yield Disk(**dev)
        raise FileNotFoundError("No Drives found!")

    def list_partitions(self, drive: "Disk | None" = None):
        with open(self.this_repo("blkdev.list"), encoding="utf-8") as f:
            parsed_lsblk = jc.parse("lsblk",f.read())
            for dev in parsed_lsblk:
                if dev["type"] == "part" and (drive is None ^ dev["kname"].startswith(str(drive))):
                    yield Partition(**dev)
        raise FileNotFoundError("No Partitions Found!")

    def validate_drive(self, drive: "Disk"):
        partitions = self.list_partitions()
        matches = [re.match(DYNAMIC_FILES["drive"], x) for x in listdir(self.img)]
        for file in matches:
            if file and file.group(1) == drive.kname:
                with open(self.this_repo("parts"), encoding="utf-8") as f:
                    parts = f.read().split(' ')
                    for part in parts:
                        self.validate_partition(part)

    def validate_partition(self, partition: "Partition"):
        pass

    def this_repo(self, file):
        return join(self.path, file)

class Disk:
    def __init__(self, kname, name, size, type, model):
        self.kname = kname
        self.name = name
        self.size = size
        self.type = type
        self.model = model
    def __str__(self):
        return self.kname

class Partition:
    def __init__(self, kname, name, size, type, fstype):
        self.kname = kname
        self.name = name
        self.size = size
        self.type = type
        self.fstype = fstype
    def __str__(self):
        return self.kname