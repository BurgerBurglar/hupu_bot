import asyncio
from datetime import datetime, timedelta

from read_posts import read_posts
from send_posts import send_posts
from utils import archive_floors

if __name__ == "__main__":
    sub_name = "lol"
    try:
        with open(f"data/{sub_name}/last_run_timestamp.txt", encoding="utf-8") as f:
            last_run_timestamp = datetime.fromisoformat(f.read())
            time_ago = datetime.now() - last_run_timestamp
    except (FileNotFoundError, ValueError):
        time_ago = timedelta(minutes=45)

    result = read_posts(sub_name, 5, time_ago)

    with open(f"data/{sub_name}/last_run_timestamp.txt", "w", encoding="utf-8") as f:
        f.write(datetime.now().isoformat())

    asyncio.run(send_posts(sub_name, reply_type="keyword"))
    archive_floors(sub_name)
