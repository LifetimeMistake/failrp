"""File containing Utility class for kernel parameters"""

class KernelCmdlineParser(dict):
    """Utility class for kernel parameters"""

    def __init__(self):
        with open("/proc/cmdline", "r", encoding="utf-8") as _f:
            self.cmdline = _f.read().strip()

        self.data = {}
        for element in self.cmdline.split():
            key, value = element, True
            if "=" in element:
                key, value = element.split("=", 1)
            if key not in self.data:
                self.data[key] = []
            self.data[key].append(value)
        super().__init__(self.data)
