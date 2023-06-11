"""Utility Classes for managing Volumes"""
from .partitioning import Disk, Partition
import yaml

class Volume:
    """Defines a Volume"""
    def __init__(self, name: str, target: "Partition | None", index: int):
        self.name = name
        self.target = target
        self.index = index

    @property
    def is_available(self):
        """Checks if volume exists on computer"""
        return self.target is not None

def parse_volume_file(volume_file: str) -> "list[Volume]":
    """Parses a Volume Definition yaml file"""
    volumes = []
    volumes_data = yaml.safe_load(volume_file)
    for name, data in volumes_data.get('volumes', {}).items():
        # Get index
        index = data.get("index")
        if index is None:
            raise ValueError(f"Volume {name} is missing required 'index' property")

        volume = Volume(name=name, target=None, index=index)
        volumes.append(volume)

    return volumes

class VolumeManager:
    """Manages Volumes on computer"""
    def __init__(self,
                 root_drive: Disk,
                 local_repo: "Partition | None" = None,
                 volume_file: "str | None" = None):
        self.root = root_drive
        self.local_repo = local_repo
        self.volumes = {}

        if volume_file:
            self.sync(volume_file)

    def sync(self, volume_file: str):
        """Synchronizes local volumes.
            if VolumeFile provided, overrides the volume schema"""
        if volume_file:
            self.volumes = {}
            volumes = parse_volume_file(volume_file)
            for volume in volumes:
                self.volumes[volume.name] = volume

        for name, volume in self.volumes.items():
            target_path = f"{self.root.path}{volume.index}"
            target_part = None
            for part in self.root.partitions:
                if part.path.startswith(self.root.path) and part.path.endswith(str(volume.index)):
                    if self.local_repo is not None and self.local_repo.path.startswith(self.root.path) and self.local_repo.path.endswith(str(volume.index)):
                        raise ValueError(f"Volume {name} targets the local image repository. \
                                        Executing operations on this partition is not allowed.")

                    target_part = part
                    break

            volume.target = target_part

    def get(self, name, default=None):
        """returns given volume from name"""
        return self.volumes.get(name, default)

    def __getitem__(self, name):
        return self.volumes[name]

    def __len__(self) -> int:
        return len(self.volumes)

    def __contains__(self, name):
        return name in self.volumes
