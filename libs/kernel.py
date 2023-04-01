"""File containing Utility class for kernel parameters"""

class KernelCmdlineParser:
    """Utility class for kernel parameters"""
    def __init__(self):
        with open("/proc/cmdline", "r") as f:
            self.cmdline = f.read().strip()

        self.data = {}
        for element in self.cmdline.split():
            key, value = element, True
            if "=" in element:
                key, value = element.split("=", 1)
            if key not in self.data:
                self.data[key] = []
            self.data[key].append(value)

    def get(self, key):
        if key not in self.data:
            return None
        
        value = self.data[key]
        if len(value) == 1:
            return value[0]
        
        return value
    
    def __contains__(self, key):
        return key in self.data