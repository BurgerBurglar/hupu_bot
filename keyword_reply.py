import pandas as pd
import json

sub_name = "lol"

dtypes = {"keyword": str, "aliases": str, "replies": str}
df = pd.read_csv(f"data/{sub_name}/input/keyword_reply.csv", dtype=dtypes)
df = df.fillna("")
keyword_reply = {}
for _, row in df.iterrows():
    keyword_reply[row["keyword"]] = row["replies"].split(";")
    for alias in row["aliases"].split(";"):
        if alias:
            keyword_reply[alias] = f"%{row['keyword']}%"
with open(f"data/{sub_name}/input/keyword_reply.json", "w", encoding="utf-8") as f:
    f.write(json.dumps(keyword_reply, indent=4, ensure_ascii=False))
