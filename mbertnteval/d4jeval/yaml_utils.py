# import pyyaml module
import yaml
from yaml.loader import SafeLoader


def load_config(config_file: str):
    # Open the file and load the file
    with open(config_file) as f:
        data = yaml.load(f, Loader=SafeLoader)
        return data