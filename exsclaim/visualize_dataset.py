import json
import pandas as pd


__all__ = ["read_jsons"]


def read_jsons(filepath) -> pd.DataFrame:
    # Open the file and read its contents
    with open(filepath, 'r') as f:
        data = f.read()
    my_dict = json.loads(data)
    rows = [{**{'name': name}, **data} for name, data in my_dict.items()]
    df = pd.DataFrame(rows)
    return df
