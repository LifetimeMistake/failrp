from rpfile_parse import RPFileParser
import io

def parse_arguments(s):
    # Split the input string into tokens
    tokens = []
    current_token = ''
    in_quote = False
    for c in s:
        if c == ' ' and not in_quote:
            if current_token:
                tokens.append(current_token)
                current_token = ''
        elif c == '"':
            in_quote = not in_quote
        else:
            current_token += c
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

def compile_instruction(type, params):
    match type:
        case "DEPLOY":
            return DeployInstruction(params)
        case "COPY":
            return CopyInstruction(params)
        case "UNPACK":
            return UnpackInstruction(params)
        case "PULL":
            return PullInstruction(params)
        case "FORMAT":
            return FormatInstruction(params)
        case _:
            # Unknown instruction
            return Instruction(type, params)


class Instruction:
    def __init__(self, type, params):
        self.type = type
        self.params = params

    def __str__(self):
        return "{type} {params}".format(type=self.type, params=" ".join([f"\"{x}\"" for x in self.params]))


class DeployInstruction(Instruction):
    def __init__(self, params):
        if len(params) != 2:
            raise ValueError(f"Invalid deploy instruction signature: {len(params)} params, expected 2")

        source_image = params[0].strip()
        target_volume = params[1].strip()

        if source_image == "":
            raise ValueError("Invalid source image definition")

        if target_volume == "":
            raise ValueError("Invalid target volume definition")

        super(DeployInstruction, self).__init__("DEPLOY", params)
        self.image = source_image
        self.volume = target_volume


class CopyInstruction(Instruction):
    def __init__(self, params):
        if len(params) != 2:
            raise ValueError(f"Invalid copy instruction signature: {len(params)} params, expected 2")

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


class UnpackInstruction(Instruction):
    def __init__(self, params):
        if len(params) != 2:
            raise ValueError(f"Invalid unpack instruction signature: {len(params)} params, expected 2")

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

class PullInstruction(Instruction):
    def __init__(self, params):
        if len(params) != 1:
            raise ValueError(f"Invalid pull instruction signature: {len(params)} params, expected 1")

        image = params[0].strip()
        if image == "":
            raise ValueError("Invalid source image definition")

        super(PullInstruction, self).__init__("PULL", params)
        self.image = image

class FormatInstruction(Instruction):
    def __init__(self, params):
        if len(params) != 2:
            raise ValueError(f"Invalid format instruction signature: {len(params)} params, expected 2")

        target_volume = params[0].strip()
        new_filesystem = params[1].strip()

        if target_volume == "":
            raise ValueError("Invalid target volume definition")

        if new_filesystem == "":
            raise ValueError("Invalid filesystem type definition")

        super(FormatInstruction, self).__init__("FORMAT", params)
        self.volume = target_volume
        self.fstype = new_filesystem

class RPFile:
    def __init__(self, source=None):
        self.instructions: list[Instruction] | None = None
        if source:
            self.compile(source)

    def compile(self, source):
        source_bytes = source.encode("utf-8")
        instructions = []
        with io.BytesIO(source_bytes) as f:
            parser = RPFileParser(fileobj=f)
            self.instructions = []
            for step in parser.structure:
                type = step["instruction"].upper()
                params = parse_arguments(step["value"])
                instructions.append(compile_instruction(type, params))

        self.instructions = instructions

    def add_instruction(self, instruction):
        self.instructions.append(instruction)

    def remove_instruction(self, instruction):
        self.instructions.remove(instruction)

    @property
    def required_images(self):
        images = []
        for instruction in self.instructions:
            if hasattr(instruction, "image"):
                images.append(instruction.image)

        return images

    @property
    def required_volumes(self):
        volumes = []
        for instruction in self.instruction:
            if hasattr(instruction, "volume"):
                volumes.append(instruction.volume)

        return volumes