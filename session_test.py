from datetime import datetime, timedelta
import json
from read_posts import ReadPost

if __name__ == "__main__":
    start_time = datetime.now()
    read_post = ReadPost(
        queries=["#皇马#"],
        sub_pages_to_read=5,
        time_ago=timedelta(days=1),
    )
    result = read_post.get_all_floors()
    print(result)
    print("Time:", datetime.now() - start_time)

    with open("view.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False))
