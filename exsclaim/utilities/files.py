"""Functions for reading and writing files."""
import yaml


__all__ = ["load_yaml"]


def load_yaml(filename):
    with open(filename, "r") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
