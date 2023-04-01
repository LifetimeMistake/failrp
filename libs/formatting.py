import shutil
import os
import os.path as path
from .partitioning import Partition
from sh import Command

def get_supported_filesystems():
    filesystems = []
    mkfs_path = shutil.which("mkfs")
    if mkfs_path:
        dir = path.dirname(mkfs_path)
        for file in os.listdir(dir):
            if not file.startswith("mkfs."):
                continue
                
            fs = '.'.join(path.basename(file).split('.')[1:])
            filesystems.append(fs)

    return filesystems

def format_partition(part: Partition, fs: str, verbose=False):
    supported_filesystems = get_supported_filesystems()
    if fs not in get_supported_filesystems():
        raise ValueError(f"Unsupported filesystem provided: '{fs}', supported filesystems: '{', '.join(supported_filesystems)}")

    format_command = Command(f"mkfs.{fs}")
    if verbose:
        format_command("-F", part.path, _fg=True)
    else:
        format_command("-F", part.path)