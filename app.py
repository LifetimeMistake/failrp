from libs.kernel import KernelCmdlineParser
from libs.repositories import ImageRepository, ConfigRepository
from libs.volumes import VolumeManager
from libs.partitioning import Disk
from libs.execution import RPFileExecutor
from libs.picker import AnsiPicker
from libs.pretty import setup
from libs.constants import DEFAULT_REMOTE_MOUNTPOINT, DEFAULT_CACHE_MOUNTPOINT, DEFAULT_CACHE_LABEL, DEFAULT_PORT
import requests, logging

cmdline = KernelCmdlineParser()

wrapper, print, console, status, _logger, progress = setup()

REMOTE_MOUNTPOINT=cmdline.get("remote_mountpoint") or DEFAULT_REMOTE_MOUNTPOINT
CACHE_MOUNTPOINT=cmdline.get("cache_mountpoint") or DEFAULT_CACHE_MOUNTPOINT
CACHE_LABEL=cmdline.get("cache_label") or DEFAULT_CACHE_LABEL
HOST=cmdline.get("host")
PORT=int(cmdline.get("port") or DEFAULT_PORT)
VOLUMEFILE = requests.get(f"http://{HOST}:{PORT}/labels", timeout=10)

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

picker = AnsiPicker(config_repo.configs)
selected_config = picker.ask(15)

with wrapper:
  executor = RPFileExecutor(selected_config, image_repo, volume_man)
  executor.compile()
  executor.execute()