import asyncio
from datetime import timedelta
import logging
from sys import argv

from read_posts import read_posts
from send_posts import send_posts

if __name__ == "__main__":
    logging.basicConfig(
        filename="logs",
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        encoding="utf-8",
    )
    if len(argv) == 1:
        sub_name = "bxj"
    else:
        sub_name = argv[1]
    reply_type = "licking_dog"
    time_ago = timedelta(minutes=30)

    logging.info("STARTING")
    result = read_posts(sub_name, 10, time_ago, reply_type=reply_type)
    logging.info("SENDING")
    asyncio.run(send_posts(sub_name, reply_type=reply_type, debug=False))
