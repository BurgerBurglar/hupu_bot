import asyncio
from datetime import timedelta
from sys import argv

from read_posts import read_posts
from send_posts import send_posts

if __name__ == "__main__":
    if len(argv) == 1:
        sub_name = "realmadrid"
    else:
        sub_name = argv[1]
    reply_type = "licking_dog"
    time_ago = timedelta(minutes=30)

    result = read_posts(sub_name, 5, time_ago, reply_type=reply_type)

    asyncio.run(send_posts(sub_name, reply_type=reply_type, debug=False))
