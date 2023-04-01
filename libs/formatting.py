"""Utility Classes for Partition Management"""
import shutil
import os
import os.path as path
from .partitioning import Partition
from sh import Command

def get_supported_filesystems():
    """returns supported Filesystems"""
    filesystems = []
    mkfs_path = shutil.which("mkfs")
    if mkfs_path:
        _dir = path.dirname(mkfs_path)
        for file in os.listdir(_dir):
            if not file.startswith("mkfs."):
                continue

            _fs = '.'.join(path.basename(file).split('.')[1:])
            filesystems.append(_fs)

    return filesystems

def format_partition(part: Partition, _fs: str, verbose=False):
    """Formats partition to given type"""
    supported_filesystems = get_supported_filesystems()
    if _fs not in get_supported_filesystems():
        raise ValueError(f"Unsupported filesystem provided: '{_fs}', supported filesystems: \
                         '{', '.join(supported_filesystems)}")

    format_command = Command(f"mkfs.{_fs}")
    if verbose:
        format_command("-F", part.path, _fg=True)
    else:
        format_command("-F", part.path)
