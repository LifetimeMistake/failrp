"""Program run before failRP client to bootstrap the environment"""
import time
from banner import banner
from rich.style import Style
from rich.text import Text
from libs.partitioning import Partition
from libs.kernel import KernelCmdlineParser
from sh import mount, beep, mkdir
from pretty import setup as r_setup


wrapper, print, console, status, logger, _ = r_setup()

cmdline = KernelCmdlineParser()

REMOTE_MOUNTPOINT=cmdline.get("remote_mountpoint") or "/mnt/repo"
CACHE_MOUNTPOINT=cmdline.get("cache_mountpoint") or "/mnt/cache"
CACHE_LABEL=cmdline.get("cache_label") or "FAILRP_CACHE"
ERROR_TIMEOUT=30

print(Text(banner(), style=Style(color="blue")))

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
        #mount -o nolock,hard,timeo=10 -t nfs host:repo_path
        mkdir("-p", REMOTE_MOUNTPOINT)
        mount("-o", "nolock,hard,timeo=10", "-t", "nfs", f"{host}:{repo_path}", REMOTE_MOUNTPOINT)
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
        return False

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
