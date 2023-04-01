from __future__ import annotations
from abc import abstractmethod, ABC
import os
import os.path as path
import tempfile
import shutil
from .rpfile import RPFile, DeployInstruction, PullInstruction, \
    CopyInstruction, UnpackInstruction, FormatInstruction
from .formatting import get_supported_filesystems, format_partition
from .repositories import ImageRepository
from .volumes import VolumeManager
from .imaging import deploy_image
from sh import mount, umount

class Operation(ABC):
    """Generic Operation Class"""

    @abstractmethod
    def execute(self):
        """executes operation"""

class DeployOperation(Operation):
    """Operation Class For Deploying a image"""
    def __init__(self, executor: RPFileExecutor, instruction: DeployInstruction):
        image = executor.image_repo.get(instruction.image)
        source_volume = instruction.image_volume
        destination = executor.volume_man.get(instruction.volume)

        if not image or (not image.available_local and not image.available_remote):
            raise FileNotFoundError(f"Image '{instruction.image}' unavailable")

        if not destination:
            raise NameError(f"Deploy destination '{destination.name}' is not defined")

        if not destination.is_available:
            raise FileNotFoundError(f"Deploy destination '{destination.name}' \
                                    unavailable on this system")

        self.image = image
        self.source_volume = source_volume
        self.target_part = destination.target

    def execute(self):
        if not self.image.best_path:
            raise FileNotFoundError("Image is unavailable")

        print(f"Deploying {self.image.name} to {self.target_part.path}...")
        print(f"Using {self.image.best_path}")
        deploy_image(self.image, self.target_part, self.source_volume)

class PullOperation(Operation):
    """OperationClass for pulling a repository to device"""
    def __init__(self, executor: RPFileExecutor, instruction: PullInstruction):
        image = executor.image_repo.get(instruction.image)

        if not image or (not image.available_local and not image.available_remote):
            raise FileNotFoundError(f"Image '{instruction.image}' unavailable")

        self.executor = executor
        self.image_name = image.name

    def execute(self):
        print(f"Pulling {self.image_name}...")
        # Get image blacklist
        blacklist = []
        for _op in self.executor.executed_operations:
            if isinstance(_op, PullOperation):
                blacklist.append(_op.image_name)

        self.executor.image_repo.pull(self.image_name, disallowed_deletions=blacklist)

class CopyOperation(Operation):
    """Operation Class for copying a file to device"""
    def __init__(self, executor: RPFileExecutor, instruction: CopyInstruction):
        image = executor.image_repo.get(instruction.image)
        destination = executor.volume_man.get(instruction.volume)

        if not image or (not image.available_local and not image.available_remote):
            raise FileNotFoundError(f"Image '{instruction.image}' unavailable")

        if not destination:
            raise NameError(f"Deploy destination '{destination.name}' is not defined")

        if not destination.is_available:
            raise FileNotFoundError(f"Copy destination '{destination.name}' \
                                    unavailable on this system")

        self.image = image
        self.target_part = destination.target
        self.destination_path = instruction.path

    def execute(self):
        if not self.image.best_path:
            raise FileNotFoundError("Image is unavailable")

        mount_path = tempfile.mkdtemp()
        print(f"Mounting {self.target_part.path} at {mount_path}")
        mount(self.target_part.path, mount_path)

        try:
            volume_path = self.destination_path.lstrip('/')
            destination_path = path.join(mount_path, volume_path)
            destination_dir = path.dirname(destination_path)
            if not path.isdir(destination_dir):
                raise FileNotFoundError(f"Path '/{path.dirname(volume_path)}' \
                                        does not exist in the target volume.")

            print(f"Copying {self.image.name} to {destination_path}...")
            print(f"Using {self.image.best_path}")
            shutil.copy(self.image.best_path, destination_path)
        finally:
            umount(mount_path)
            os.rmdir(mount_path)
            print("Unmounted working volume")

class UnpackOperation(Operation):
    """Operation Class for Unzipping archives to device"""
    def __init__(self, executor: RPFileExecutor, instruction: CopyInstruction):
        image = executor.image_repo.get(instruction.image)
        destination = executor.volume_man.get(instruction.volume)

        if not image or (not image.available_local and not image.available_remote):
            raise FileNotFoundError(f"Image '{instruction.image}' unavailable")

        ext = f".{'.'.join(path.basename(image.best_path).split('.')[1:])}"
        supported_exts = []
        for _type, exts, _name in shutil.get_unpack_formats():
            supported_exts.extend(exts)

        if ext not in supported_exts:
            raise NotImplementedError(f"Image archive format '{ext}' not supported. \
                                      Supported formats: '{', '.join(supported_exts)}'")

        if not destination:
            raise NameError(f"Deploy destination '{destination.name}' is not defined")

        if not destination.is_available:
            raise FileNotFoundError(f"Copy destination '{destination.name}' \
                                    unavailable on this system")

        self.image = image
        self.target_part = destination.target
        self.destination_path = instruction.path

    def execute(self):
        if not self.image.best_path:
            raise FileNotFoundError("Image is unavailable")

        mount_path = tempfile.mkdtemp()
        print(f"Mounting {self.target_part.path} at {mount_path}")
        mount(self.target_part.path, mount_path)

        try:
            volume_path = self.destination_path.lstrip('/')
            destination_path = path.join(mount_path, volume_path)
            destination_dir = path.dirname(destination_path)
            if not path.isdir(destination_dir):
                raise FileNotFoundError(f"Path '/{path.dirname(volume_path)}' \
                                        does not exist in the target volume.")

            print(f"Unpacking {self.image.name} to {destination_path}...")
            print(f"Using {self.image.best_path}")
            shutil.unpack_archive(self.image.best_path, destination_path)
        finally:
            umount(mount_path)
            os.rmdir(mount_path)
            print("Unmounted working volume")

class FormatOperation(Operation):
    """Operation Class for Formatting a partition on device"""
    def __init__(self, executor: RPFileExecutor, instruction: FormatInstruction):
        fstype = instruction.fstype
        destination = executor.volume_man.get(instruction.volume)

        supported_filesystems = get_supported_filesystems()
        if fstype not in get_supported_filesystems():
            raise ValueError(f"Unsupported filesystem provided: '{fstype}', \
                             supported filesystems: '{', '.join(supported_filesystems)}")

        if not destination:
            raise NameError(f"Format target '{destination.name}' is not defined")

        if not destination.is_available:
            raise FileNotFoundError(f"Copy destination '{destination.name}' \
                                    is unavailable on this system")

        self.fstype = fstype
        self.target_part = destination.target

    def execute(self):
        print(f"Formatting {self.target_part.path} to {self.fstype}...")
        format_partition(self.target_part, self.fstype, verbose=True)

class RPFileExecutor:
    """RPFile execution class"""
    def __init__(self, rpfile: RPFile, image_repo: ImageRepository, volume_man: VolumeManager):
        self.rpfile = rpfile
        self.image_repo = image_repo
        self.volume_man = volume_man
        self.operations = None
        self.executed_operations = None

    def compile(self, skip_unsupported=True):
        """Only God knows what happens here"""
        operations = []
        instructions = self.rpfile.instructions

        print("Starting build")
        for i, instruction in enumerate(instructions):
            print(f"[{i+1}/{len(instructions)}] {instruction}")
            try:
                # YandereDev Coding momentos
                if isinstance(instruction, DeployInstruction):
                    operation = DeployOperation(self, instruction)
                elif isinstance(instruction, PullInstruction):
                    operation = PullOperation(self, instruction)
                elif isinstance(instruction, CopyInstruction):
                    operation = CopyOperation(self, instruction)
                elif isinstance(instruction, UnpackInstruction):
                    operation = UnpackOperation(self, instruction)
                elif isinstance(instruction, FormatInstruction):
                    operation = FormatOperation(self, instruction)
                else:
                    if skip_unsupported:
                        print(f"Skipping unsupported instruction type: {type(instruction)}")
                        continue
                    else:
                        raise (f"Unsupported instruction type: {type(instruction)}")
            except Exception as ex:
                print("Build failed!")
                print(f"ERROR: {ex}")
                return False

            operations.append(operation)

        self.operations = operations
        return True

    def execute(self):
        """Executes RPFile"""
        print("Starting execution")
        self.executed_operations = []

        if not self.operations:
            raise RuntimeError("Executor was not compiled! \
                               Use .compile() to build an operation list.")

        for i, _op in enumerate(self.operations):
            print(f"Executing operation {i+1} of {len(self.operations)}: {type(_op).__name__}")
            try:
                _op.execute()
            except Exception as ex:
                print("Execution failed!")
                print(f"ERROR: {ex}")
                return False

            self.executed_operations.append(_op)

        print("Done executing RPFile")
        self.executed_operations.clear()
        return True
