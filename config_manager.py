import os
import json

class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._init_config()
        return cls._instance

    def _init_config(self):
        # Save settings in the AppData folder to persist across updates
        local_app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        self.config_dir = os.path.join(local_app_data, 'MT_Tool')
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
            except:
                pass
                
        self.config_file = os.path.join(self.config_dir, 'settings.json')
        self.default_config = {
            'vt_enabled': False,
            'vt_api_key': '',
            'download_folder': os.path.join(os.path.expanduser('~'), 'Downloads')
        }
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Merge with default to ensure all keys exist
                    for k, v in self.default_config.items():
                        if k not in data:
                            data[k] = v
                    return data
            except Exception as e:
                print(f"Error loading config: {e}")
        return self.default_config.copy()

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

# Global instance
config = ConfigManager()
