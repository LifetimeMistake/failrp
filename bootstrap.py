from banner import banner
from libs.partitioning import Partition
from libs.kernel import KernelCmdlineParser
from sh import mount, beep, mkdir
import time

cmdline = KernelCmdlineParser()

REMOTE_MOUNTPOINT=cmdline.get("remote_mountpoint") or "/mnt/repo"
CONFIGS_MOUNTPOINT=cmdline.get("configs_mountpoint") or "/mnt/configs"
CACHE_MOUNTPOINT=cmdline.get("cache_mountpoint") or "/mnt/cache"
CACHE_LABEL=cmdline.get("cache_label") or "FAILRP_CACHE"
ERROR_TIMEOUT=30

print(banner())

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
    print(f"Connecting to image repo {repo_path} at {host}...")

    try:
        #mount -o nolock,hard,timeo=10 -t nfs host:repo_path 
        mkdir("-p", REMOTE_MOUNTPOINT)
        mount("-o", "nolock,hard,timeo=10", "-t", "nfs", f"{host}:{repo_path}", REMOTE_MOUNTPOINT)
    except Exception as ex:
        print(f"Mount error: {ex}")
        return False

    return True

# def setup_configs_repo():
#     if not check_params(["host", "configs"]):
#         return False

#     host = cmdline.get("host")
#     repo_path = cmdline.get("configs")
#     print(f"Connecting to config repo {repo_path} at {host}...")

#     try:
#         #mount -o nolock,hard,timeo=10 -t nfs host:repo_path 
#         mkdir("-p", CONFIGS_MOUNTPOINT)
#         mount("-o", "nolock,hard,timeo=10", "-t", "nfs", f"{host}:{repo_path}", CONFIGS_MOUNTPOINT)
#     except Exception as ex:
#         print(f"Mount error: {ex}")
#         return False

#     return True

def setup_local_repo():
    print("Enumerating partitions...")
    local_cache_part = None
    for part in Partition.get_all().values():
        print(f"{part.path} {part.fstype} {part.fsuuid} {part.fslabel}")
        if not part.removable and part.fslabel == CACHE_LABEL:
            local_cache_part = part
            break

    if not local_cache_part:
        print("Local repo not found")
        return False
    
    try:
        local_cache_part.mount(CACHE_MOUNTPOINT, True)
    except Exception as ex:
        print(f"Mount error: {ex}")
        return False
    
    return True

def main():
    if not setup_remote_repo() or not setup_local_repo():
        print("Bootstrap failed")
        for i in range(ERROR_TIMEOUT):
            print(f"Exiting in {ERROR_TIMEOUT-i}...")
            beep()
            time.sleep(1)

        return
    
    print("Bootstrap OK")
    
if __name__ == "__main__":
    main()