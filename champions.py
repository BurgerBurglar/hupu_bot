import pandas as pd
import json


def get_champion_map(df, col):
    return {i: df[df[col] == i]["id"].iloc[0] for i in df[col]}


df = pd.read_csv("champions.csv").fillna("")
champions = {}
for i, line in enumerate(df["aliases"]):
    if line:
        aliases = line.split(" ")
        for alias in aliases:
            champions[alias] = df["id"].iloc[i]
champions = (
    champions
    | get_champion_map(df, "name_en")
    | get_champion_map(df, "title_cn")
    | get_champion_map(df, "name_cn")
)
with open("champion_alias.json", "w", encoding="utf-8") as f:
    j = json.dumps(champions, indent=4, ensure_ascii=False)
    f.write(j)
