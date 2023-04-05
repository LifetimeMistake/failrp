"""Program run before failRP client to bootstrap the environment"""
import time
from banner import banner
from rich.style import Style
from rich.text import Text
from libs.partitioning import Partition, Disk
from libs.formatting import format_partition
from libs.kernel import KernelCmdlineParser
from libs.picker import AnsiPicker
from libs.constants import DEFAULT_REMOTE_MOUNTPOINT, DEFAULT_CACHE_MOUNTPOINT, DEFAULT_CACHE_LABEL
from sh import mount, beep, mkdir, cfdisk
from libs.pretty import setup as r_setup

wrapper, print, console, status, logger, _ = r_setup()

cmdline = KernelCmdlineParser()

REMOTE_MOUNTPOINT = cmdline.get(
    "remote_mountpoint") or DEFAULT_REMOTE_MOUNTPOINT
CACHE_MOUNTPOINT = cmdline.get("cache_mountpoint") or DEFAULT_CACHE_MOUNTPOINT
CACHE_LABEL = cmdline.get("cache_label") or DEFAULT_CACHE_LABEL
ERROR_TIMEOUT = 10

print(Text(banner(), style=Style(color="blue")))

def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

def create_local_repo():
    options = {}
    for path, part in Partition.get_all().items():
        label = f"{path} {sizeof_fmt(part.size)}"
        options[label] = part

    options["Create new"] = "new"
    options["Cancel"] = "cancel"

    picker = AnsiPicker(options)
    picked = picker.ask(15, default_key=None, msg="Choose an existing partition or repartition your drive")

    if picked == "cancel":
        return None
    elif picked == "new":
        options = {}
        for path, disk in Disk.get_all().items():
            label = f"{path} {sizeof_fmt(disk.size)}"
            options[label] = disk

        options["Cancel"] = False
        picker = AnsiPicker(options)
        picked = picker.ask(15, default_key=None, msg="Choose a disk to work on")
        if not picked:
            return None

        logger.info("Now entering cfdisk")
        cfdisk(picked.path, _fg=True)
        # recurse
        return create_local_repo()
    
    return picked

def check_params(params):
    for param in params:
        if param not in cmdline:
            logger.error(f"Missing required boot parameter: {param}")
            return False

    return True

def setup_remote_repo():
    """mounts remote repository"""
    if not check_params(["host", "repo"]):
        return False

    host = cmdline.get("host")
    repo_path = cmdline.get("repo")
    logger.info(f"Connecting to image repo {repo_path} at {host}...")

    try:
        # mount -o nolock,hard,timeo=10 -t nfs host:repo_path
        mkdir("-p", REMOTE_MOUNTPOINT)
        mount("-o", "nolock,hard,timeo=10", "-t", "nfs",
              f"{host}:{repo_path}", REMOTE_MOUNTPOINT)
    except Exception as ex:
        logger.exception(f"Mount error: {ex}")
        return False

    return True

def setup_local_repo():
    """mounts cache"""
    logger.info("Enumerating partitions...")
    local_cache_part = None
    for part in Partition.get_all().values():
        logger.debug(f"{part.path} {part.fstype} {part.fsuuid} {part.fslabel}")
        if not part.removable and part.fslabel == CACHE_LABEL:
            local_cache_part = part
            break

    if not local_cache_part:
        logger.warning("Local repo not found")
        local_cache_part: Partition = create_local_repo()
        if not local_cache_part:
            return False

        format_partition(local_cache_part, "ext4")
        local_cache_part.set_fslabel(CACHE_LABEL)

    try:
        local_cache_part.mount(CACHE_MOUNTPOINT, True)
    except Exception as ex:
        logger.exception(f"Mount error: {ex}")
        return False

    return True

def main():
    """Start method"""
    if not setup_remote_repo() or not setup_local_repo():
        logger.error("Bootstrap failed")
        for i in range(ERROR_TIMEOUT):
            print(f"Exiting in {ERROR_TIMEOUT-i}...")
            beep()
            time.sleep(1)

        return

    logger.info("Bootstrap OK")

if __name__ == "__main__":
    main()
