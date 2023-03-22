from os.path import exists, abspath
from os import listdir, system
import subprocess
from hashlib import md5
from rpfile_parse import RPFileParser
from sh import Command
ocs_sr = Command("ocs-sr")

def nfs_mount():
    return exists("/mnt/repo")

rp_file = RPFileParser("./")



def ocs_restore(image_file, image_backup_partition, partition):
    cmd = ["ocs-sr", "-e1", "auto", "-e2", "-r", "-c", "-k", "-p", "choose", "-f", partition, "restoreparts", image_file, image_backup_partition]
    ocs_sr(cmd)

def check_cache(files: str):
    if exists("/mnt/cache"):
        if nfs_mount():
            for file in files:
                with open(file) as f:
                    pass