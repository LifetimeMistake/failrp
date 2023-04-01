"""Utility Classes for RPfile Parsing"""
import io
from rpfile_parse import RPFileParser

def parse_arguments(_s):
    """Parses String Arguments into a list"""
    # Split the input string into tokens
    tokens = []
    current_token = ''
    in_quote = False
    for _c in _s:
        if _c == ' ' and not in_quote:
            if current_token:
                tokens.append(current_token)
                current_token = ''
        elif _c == '"':
            in_quote = not in_quote
        else:
            current_token += _c
    if current_token:
        tokens.append(current_token)
    # Remove quotes from the tokens
    args = []
    for token in tokens:
        if token.startswith('"') and token.endswith('"'):
            args.append(token[1:-1])
        else:
            args.append(token)
    if "TO" in args:
        args.pop(args.index("TO"))
    return args

def compile_instruction(instrucion_type, params):
    """Chooses Class for given instruction"""
    if instrucion_type == "DEPLOY":
        return DeployInstruction(params)
    elif instrucion_type == "COPY":
        return CopyInstruction(params)
    elif instrucion_type == "UNPACK":
        return UnpackInstruction(params)
    elif instrucion_type == "PULL":
        return PullInstruction(params)
    elif instrucion_type ==  "FORMAT":
        return FormatInstruction(params)
    else:
        # Unknown instruction
        return Instruction(instrucion_type, params)

class Instruction:
    """Instruction Headclass"""
    def __init__(self, instruction_type, params):
        self.type = instruction_type
        self.params = params

    def __str__(self):
        return f'{self.type} {" ".join([F"`{x}`" for x in self.params])}'


class DeployInstruction(Instruction):
    """A instruction wrapper for Deploying a image"""
    def __init__(self, params):
        if len(params) != 2:
            raise ValueError(f"Invalid deploy instruction signature: \
                             {len(params)} params, expected 2")

        source = params[0].strip().split(":")
        if len(source) > 2:
            raise ValueError("Invalid source definition, too many parameters")

        source_image = source[0].strip()
        source_volume = source[1].strip() if len(source) == 2 else None
        target_volume = params[1].strip()

        if source_image == "":
            raise ValueError("Invalid source image definition")

        if source_volume == "":
            raise ValueError("Invalid source volume definition")

        if target_volume == "":
            raise ValueError("Invalid target volume definition")

        super(DeployInstruction, self).__init__("DEPLOY", params)
        self.image = source_image
        self.image_volume = source_volume
        self.volume = target_volume

    def __str__(self):
        return f"DEPLOY \
            {self.image}{(f':{self.image_volume}' if self.image_volume else '')} \
            {self.volume}"

class CopyInstruction(Instruction):
    """Instruction Wrapper for copying files"""
    def __init__(self, params):
        if len(params) != 2:
            raise ValueError(f"Invalid copy instruction signature: \
                            {len(params)} \
                            params, expected 2")

        source_image = params[0].strip()
        target = params[1].split(":")

        if source_image == "":
            raise ValueError("Invalid source image definition")

        if len(target) == 2:
            target_path = target[1].strip()
            if target_path == "":
                target_path = "/"
        elif len(target) == 1:
            target_path = "/"
        else:
            raise ValueError(f"Invalid destination path definition: \"{params[1]}\"")

        target_volume = target[0].strip()

        if target_volume == "":
            raise ValueError("Invalid target volume definition")

        super(CopyInstruction, self).__init__("COPY", params)
        self.image = source_image
        self.volume = target_volume
        self.path = target_path

    def __str__(self):
        return f"COPY {self.image} {self.volume}:{self.path}"

class UnpackInstruction(Instruction):
    """Instruction class for unzipping files"""
    def __init__(self, params):
        if len(params) != 2:
            raise ValueError(f"Invalid unpack instruction signature: \
                            {len(params)} \
                            params, expected 2")

        source_image = params[0].strip()
        target = params[1].split(":")

        if source_image == "":
            raise ValueError("Invalid source image definition")

        if len(target) == 2:
            target_path = target[1].strip()
            if target_path == "":
                target_path = "/"
        elif len(target) == 1:
            target_path = "/"
        else:
            raise ValueError(f"Invalid destination path definition: \"{params[1]}\"")

        target_volume = target[0].strip()

        if target_volume == "":
            raise ValueError("Invalid target volume definition")

        super(UnpackInstruction, self).__init__("UNPACK", params)
        self.image = source_image
        self.volume = target_volume
        self.path = target_path

    def __str__(self):
        return f"UNPACK {self.image} {self.volume}:{self.path}"

class PullInstruction(Instruction):
    """Instruction wrapper for pulling a repository"""
    def __init__(self, params):
        if len(params) != 1:
            raise ValueError(f"Invalid pull instruction signature: \
                            {len(params)} \
                            params, expected 1")

        image = params[0].strip()
        if image == "":
            raise ValueError("Invalid source image definition")

        super(PullInstruction, self).__init__("PULL", params)
        self.image = image

    def __str__(self):
        return f"PULL {self.image}"

class FormatInstruction(Instruction):
    """Instruction Wrapper for formatting a partition"""
    def __init__(self, params):
        if len(params) != 2:
            raise ValueError(f"Invalid format instruction signature: \
                            {len(params)} \
                            params, expected 2")

        target_volume = params[0].strip()
        new_filesystem = params[1].strip()

        if target_volume == "":
            raise ValueError("Invalid target volume definition")

        if new_filesystem == "":
            raise ValueError("Invalid filesystem type definition")

        super(FormatInstruction, self).__init__("FORMAT", params)
        self.volume = target_volume
        self.fstype = new_filesystem

    def __str__(self):
        return f"FORMAT {self.volume} {self.fstype}"

class RPFile:
    """RPFile type extension"""
    def __init__(self, source=None):
        self.instructions: "list[Instruction] | None" = None
        if source:
            self.compile(source)

    def compile(self, source):
        """Compiles RPFile to Python"""
        source_bytes = source.encode("utf-8")
        instructions = []
        with io.BytesIO(source_bytes) as _f:
            parser = RPFileParser(fileobj=_f)
            self.instructions = []
            for step in parser.structure:
                instrucion_type = step["instruction"].upper()
                params = parse_arguments(step["value"])
                instructions.append(compile_instruction(instrucion_type, params))

        self.instructions = instructions

    def add_instruction(self, instruction):
        """appends instruction to instruction stack"""
        self.instructions.append(instruction)

    def remove_instruction(self, instruction):
        """removes instruction from instruction stack"""
        self.instructions.remove(instruction)

    @property
    def required_images(self):
        """Lists all required files for RPfile"""
        images = []
        for instruction in self.instructions:
            if hasattr(instruction, "image"):
                images.append(instruction.image)

        return images

    @property
    def required_volumes(self):
        """Lists all required Volumes for RPfile"""
        volumes = []
        for instruction in self.instructions:
            if hasattr(instruction, "volume"):
                volumes.append(instruction.volume)

        return volumes
