import os
import json

class CreatorConfig:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CreatorConfig, cls).__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        self.config_path = os.path.join(os.getenv("APPDATA"), "BModloader", "config_creator.json")
        self.defaults = {
            "defaultAuthor": "",
            "defaultGameVersion": "All",
            "defaultModVersion": "1.0",
            "brawlhallaPath": "",
            "modsPath": "",
            "modsSourcesPath": ""
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.data = json.load(f)
            except:
                self.data = self.defaults.copy()
        else:
            self.data = self.defaults.copy()
            self._save()

    def _save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    @property
    def defaultAuthor(self):
        return self.data.get("defaultAuthor", self.defaults["defaultAuthor"])

    @defaultAuthor.setter
    def defaultAuthor(self, value):
        self.data["defaultAuthor"] = value
        self._save()

    @property
    def defaultGameVersion(self):
        return self.data.get("defaultGameVersion", self.defaults["defaultGameVersion"])

    @defaultGameVersion.setter
    def defaultGameVersion(self, value):
        self.data["defaultGameVersion"] = value
        self._save()

    @property
    def defaultModVersion(self):
        return self.data.get("defaultModVersion", self.defaults["defaultModVersion"])

    @defaultModVersion.setter
    def defaultModVersion(self, value):
        self.data["defaultModVersion"] = value
        self._save()

    @property
    def brawlhallaPath(self):
        return self.data.get("brawlhallaPath", self.defaults["brawlhallaPath"])

    @brawlhallaPath.setter
    def brawlhallaPath(self, value):
        self.data["brawlhallaPath"] = value
        self._save()

    @property
    def modsPath(self):
        return self.data.get("modsPath", self.defaults["modsPath"])

    @modsPath.setter
    def modsPath(self, value):
        self.data["modsPath"] = value
        self._save()

    @property
    def modsSourcesPath(self):
        return self.data.get("modsSourcesPath", self.defaults["modsSourcesPath"])

    @modsSourcesPath.setter
    def modsSourcesPath(self, value):
        self.data["modsSourcesPath"] = value
        self._save()
