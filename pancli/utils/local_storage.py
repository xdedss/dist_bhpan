


import json, pathlib, os, sys

def get_user_data_dir():
    home = pathlib.Path.home()

    system_paths = {
        'win32': home / 'AppData/Roaming',
        'linux': home / '.local/share',
        'darwin': home / 'Library/Application Support'
    }
    if sys.platform not in system_paths:
        return None
    else:
        return system_paths[sys.platform]

class StoredObject():


    def __init__(self, folder: str, file_name: str):
        storage_dir = os.path.join(get_user_data_dir(), folder)
        os.makedirs(storage_dir, exist_ok=True)
        self.storage_file = os.path.join(storage_dir, file_name)
        if (os.path.isfile(self.storage_file)):
            with open(self.storage_file, 'r') as f:
                self.json_obj = json.loads(f.read())
        else:
            self.json_obj = dict()
    
    def save(self):
        if (not os.path.isfile(self.storage_file)):
            print('creating config file', self.storage_file)
        s = json.dumps(self.json_obj)
        with open(self.storage_file, 'w') as f:
            f.write(s)
    
    def get_by_path(self, path, default_val=None):
        keys = path.split('/')
        current = self.json_obj
        for k in keys:
            if (k in current):
                current = current[k]
            else:
                return None
        return current
    
    def set_by_path(self, path, val, override=True):
        keys = path.split('/')
        current = self.json_obj
        for k in keys[:-1]:
            if (not k in current):
                current[k] = {}
                current = current[k]
        if (override or (keys[-1] not in current)):
            current[keys[-1]] = val

    def remove_by_path(self, path):
        keys = path.split('/')
        current = self.json_obj
        for k in keys[:-1]:
            if (k in current):
                current = current[k]
            else:
                return
        if (keys[-1] in current):
            current.pop(keys[-1])


