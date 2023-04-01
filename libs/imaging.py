from .partitioning import Partition
from .repositories import Image
import tempfile
from sh import mount, umount, Command
import os.path as path
import os

ocs_sr = Command("/usr/sbin/ocs-sr")

def mount_image(image: Image) -> str:
    if not image.available_local and not image.available_remote:
        raise FileNotFoundError("Image is not available in any repo")

    mount_dir = tempfile.mkdtemp()
    mount(image.best_path, mount_dir)
    return mount_dir

def unmount_image(mount_path: str):
    if not path.isdir(mount_path):
        return

    if path.ismount(mount_path):
        umount(mount_path)

    os.rmdir(mount_path)

def deploy_image(image: Image, target_partition: Partition, source_part=None):
    # Make sure partition is not busy
    if target_partition.mountpoint:
        umount(target_partition.mountpoint)
    
    mount_path = mount_image(image)
    parts_file = path.join(mount_path, "parts")
    try:

        if not path.isfile(parts_file):
            raise Exception("Could not find image parts definition, image may be corrupted.")

        with open(parts_file, "r") as f:
            all_parts = [line for line in f.read().strip().split(" ") if line.strip()]

        print(all_parts)

        if len(all_parts) == 0:
            raise Exception("Image does not contain any restorable partitions")

        if len(all_parts) > 1 and not source_part:
            # This function is unequipped to deal with multi-part images
            raise Exception("This deploy mechanism does not support deploying multiple partitions")

        if source_part and source_part not in all_parts:
                raise Exception(f"Image does not contain a partition called {source_part}, available parts: '{' '.join(all_parts)}'")

        if not source_part:
            # Select the only partition
            source_part = all_parts[0]

        source_dir = path.basename(mount_path)
        root_dir = path.dirname(mount_path)
        target_device = path.basename(target_partition.path)

        ocs_sr("-e1", "auto", "-e2", "-t", "-r", "-k", "-scr", "-nogui",
         "-or", root_dir, "-f", source_part, "restoreparts", source_dir, target_device, _fg=True)
    finally:
        unmount_image(mount_path)