from libs.partitioning import Partition
from libs.kernel import KernelCmdlineParser
from sh import mount, beep, mkdir
import time

cmdline = KernelCmdlineParser()

REMOTE_MOUNTPOINT="/mnt/repo"
CACHE_MOUNTPOINT="/mnt/cache"
CACHE_LABEL="FAILRP_CACHE"
    
def check_params(params):
    for param in params:
        if param not in cmdline:
            print(f"Missing required boot parameter: {param}")
            return False
        
    return True

def setup_remote_repo():
    if not check_params(["host", "repo"]):
        return False

    host = cmdline.get("host")
    repo_path = cmdline.get("repo")
    print(f"Connecting to repo {repo_path} at {host}...")

    try:
        #mount -o nolock,hard,timeo=10 -t nfs host:repo_path 
        mkdir("-p", REMOTE_MOUNTPOINT)
        mount("-o", "nolock,hard,timeo=10", "-t", "nfs", f"{host}:{repo_path}", REMOTE_MOUNTPOINT)
    except Exception as ex:
        print(f"Mount error: {ex}")
        return False

    return True

def setup_local_repo():
    print("Enumerating partitions...")
    local_cache_part = None
    for part in Partition.get_all():
        print(f"{part.path} {part.fstype} {part.uuid} {part.fslabel}")
        if not part.removable and part.fslabel == CACHE_LABEL:
            local_cache_part = part
            break

    if not local_cache_part:
        print("Local repo not found")
        return False
    
    try:
        mkdir("-p", CACHE_MOUNTPOINT)
        mount(part.path, CACHE_MOUNTPOINT)
    except Exception as ex:
        print(f"Mount error: {ex}")
        return False
    
    return True

def main():
    if not setup_remote_repo() or not setup_local_repo():
        print("Bootstrap failed")
        for i in range(10):
            print(f"Exiting in {10-i}...")
            beep()
            time.sleep(1)

        return
    
    print("Bootstrap OK")
    
if __name__ == "__main__":
    main()