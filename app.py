from libs.kernel import KernelCmdlineParser
from libs.repositories import ImageRepository, ConfigRepository
from libs.volumes import VolumeManager
from libs.partitioning import Disk
from libs.execution import RPFileExecutor
from pretty import setup

cmdline = KernelCmdlineParser()

wrapper, print, console, status, _logger, progress = setup()

REMOTE_MOUNTPOINT=cmdline.get("remote_mountpoint") or "/mnt/repo"
# CONFIGS_MOUNTPOINT=cmdline.get("configs_mountpoint") or "/mnt/configs"
CACHE_MOUNTPOINT=cmdline.get("cache_mountpoint") or "/mnt/cache"
CACHE_LABEL=cmdline.get("cache_label") or "FAILRP_CACHE"
HOST=cmdline.get("host")
PORT=int(cmdline.get("port") or 2021)

VOLUMEFILE = """
volumes:
  bootloader:
    index: 2
"""

for disk in Disk.get_all().values():
    for part in disk.partitions:
        if not part.removable and part.fslabel == CACHE_LABEL:
            root_disk = disk
            repo_part = part
            break

_logger.info(f"Using root disk {root_disk.path}")
_logger.info(f"Local repo at {repo_part.path}")

image_repo = ImageRepository(REMOTE_MOUNTPOINT, CACHE_MOUNTPOINT, True)
volume_man = VolumeManager(root_disk, repo_part, VOLUMEFILE)
config_repo = ConfigRepository(HOST, PORT, True)

while True:
    config_name = input("Select config: ")
    selected_config = config_repo.get(config_name)

    if selected_config:
        break

    print("Invalid config name")
    print(f"Available config files: {', '.join(config_repo.configs.keys())}")
with wrapper:
  executor = RPFileExecutor(selected_config, image_repo, volume_man)
  executor.compile()
  executor.execute()