import os
import os.path as path
import hashlib
import shutil
from .rpfile import RPFile

HASH_SIG = ".sha256"

def compute_hash(file):
    hash = hashlib.sha256()
    with open(file, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            hash.update(block)

    return hash.hexdigest()

def read_image_hash(image_path):
    hash_path = image_path + HASH_SIG
    if not path.isfile(hash_path):
        return None

    with open(hash_path, "r") as f:
        return f.read().strip()

def write_image_hash(image_path, hash):
    hash_path = image_path + HASH_SIG
    if hash == None:
        if path.isfile(hash_path):
            os.remove(hash_path)
        return

    with open(hash_path, "w") as f:
        f.write(hash)

def list_images(dir):
    images = []
    for file in os.listdir(dir):
        if not path.isfile(path.join(dir, file)) or file.endswith(HASH_SIG):
            continue

        images.append(file)

    return images

class Image:
    def __init__(self, name, remote_path, local_path, remote_hash, local_hash):
        self.name = name
        self.remote_path = remote_path
        self.local_path = local_path
        self.remote_hash = remote_hash
        self.local_hash = local_hash

    def pull(self, destination):
        shutil.copy(self.remote_path, destination)
        self.local_path = destination
        write_image_hash(destination, self.remote_hash)
        self.local_hash = self.remote_hash

    def delete(self):
        if path.exists(self.local_path):
            os.remove(self.local_path)
            write_image_hash(self.local_path, None)
        
        self.local_path = None
        self.local_hash = None

    @property
    def available_remote(self):
        return self.remote_path != None and self.remote_hash != None

    @property
    def available_local(self):
        return self.local_path != None

    @property
    def best_path(self):
        if self.available_local:
            return self.local_path
        
        if self.available_remote:
            return self.remote_path

        return None

    @property
    def outdated(self):
        return self.available_remote and self.available_local and self.remote_hash != self.local_hash

    @property
    def size(self):
        if self.available_local:
            return path.getsize(self.local_path)

        if self.available_remote:
            return path.getsize(self.remote_path)

        return None

class ImageRepository:
    def __init__(self, repo_path, storage_path, eager_mode=False):
        if not path.exists(repo_path):
            raise ValueError(f"Non-existent repository path provided: {repo_path}")

        if not path.exists(storage_path):
            raise ValueError(f"Non-existent image storage path provided: {storage_path}")

        self.repo_path: str = repo_path
        self.storage_path: str = storage_path
        self.images: dict[str, Image] = {}

        if eager_mode:
            self.sync()

    def sync(self):
        image_files = list(set(list_images(self.storage_path) + list_images(self.repo_path)))
        images: dict[str, Image] = {}

        # Build image list
        for name in image_files:
            try:
                local_path = path.join(self.storage_path, name)
                remote_path = path.join(self.repo_path, name)

                local_exists = path.isfile(local_path)
                remote_exists = path.isfile(remote_path)

                local_hash = read_image_hash(local_path) if local_exists else None
                remote_hash = read_image_hash(remote_path) if remote_exists else None

                if local_exists and not local_hash:
                    local_hash = compute_hash(local_path)
                    write_image_hash(local_path, local_hash)

                image = Image(
                    name,
                    remote_path if remote_exists else None,
                    local_path if local_exists else None,
                    remote_hash,
                    local_hash
                )

                images[name] = image
            except Exception as ex:
                print(f"WARNING: Failed to sync image {name}: {ex}")

        self.images = images

    def shrink_storage(self, required_free, disallowed_deletions=[]):
        free_space = self.free_storage
        local_images: list[Image] = [image for image in self.images.values() if image.available_local]

        shrinkable_space = sum([x.size for x in local_images if x.name not in disallowed_deletions])
        if free_space + shrinkable_space < required_free:
            # impossible to free space up to the required point
            return False

        # Shrink storage
        local_images = sorted(local_images, key=lambda x: x.size, reverse=True)
        for image in local_images:
            if image.name in disallowed_deletions:
                continue

            image_size = image.size
            image.delete()
            
            free_space += image_size
            if free_space > required_free:
                break

        return free_space > required_free


    def pull(self, name, force=False, allow_deletion=True, disallowed_deletions=[]):
        if name not in self.images:
            raise ValueError(f"Image {name} unavailable in repo")

        image = self.images[name]
        if not image.available_remote:
            raise FileNotFoundError(f"Image {name} unavailable in repo")

        if image.available_local:
            if not image.outdated and not force:
                # Image is up to date, don't pull
                return
            else:
                # Delete locally cached image
                image.delete()

        free_space = self.free_storage
        image_size = image.size

        if free_space < image_size:
            if not allow_deletion or not self.shrink_storage(image_size, disallowed_deletions):
                raise IOError("Insufficient storage space to save image")

        destination = path.join(self.storage_path, name)
        image.pull(destination)

    def get(self, name):
        return self.images[name]

    def get_all(self):
        return list(self.images.values())

    def get_remotes(self):
        return [image for image in self.images.values() if image.available_remote]

    def get_locals(self):
        return [image for image in self.images.values() if image.available_local]

    def __getitem__(self, name):
        return self.get(name)

    def __len__(self):
        return len(self.images)

    def __contains__(self, name):
        return name in self.images

    @property
    def free_storage(self):
        return shutil.disk_usage(self.storage_path).free

    @property
    def used_storage(self):
        return shutil.disk_usage(self.storage_path).used

    @property
    def total_storage(self):
        return shutil.disk_usage(self.storage_path).total

class ConfigRepository:
    def __init__(self, repo_path, eager_mode=False):
        if not path.exists(repo_path):
            raise ValueError(f"Non-existent repository path provided: {repo_path}")
            
        self.repo_path = repo_path
        self.configs: dict[str, RPFile] = {}

        if eager_mode:
            self.sync()

    def sync(self):
        configs: dict[str, RPFile] = {}
        for name in os.listdir(self.repo_path):
            try:
                config_path = path.join(self.repo_path, name)
                with open(config_path, "r") as f:
                    source = f.read()

                config = RPFile(source)
                configs[name] = config
            except Exception as ex:
                print(f"WARNING: Failed to sync config {name}: {ex}")

        self.configs = configs

    def get(self, name):
        return self.configs[name]

    def __getitem__(self, name):
        return self.get(name)

    def __len__(self):
        return len(self.configs)

    def __contains__(self, name):
        return name in self.configs