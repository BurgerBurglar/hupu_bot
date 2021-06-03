import re
from typing import List, Optional
import bs4
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from datetime import datetime, timedelta
from pytz import timezone
from multiprocessing import Pool
import json


class ReadPost:
    def __init__(
        self,
        queries: Optional[List[str]] = None,
        n_posts: Optional[int] = None,
        min_time: Optional[datetime] = None,
    ) -> None:
        self.website_url = "http://bbs.hupu.com"
        self.subs = ["lol"]
        self.sub_urls = [f"{self.website_url}/{sub}" for sub in self.subs]
        self.queries = queries
        self.n_posts = n_posts
        self.min_time = min_time

    def _requests_retry_session(
        retries=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
        session=None,
    ):
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def get_posts(self) -> List:
        try:
            html_text = (
                self._requests_retry_session().get(self.sub_urls[0], timeout=10).text
            )
        except requests.exceptions.ConnectionError as e:
            print(e)
            return []
        soup = BeautifulSoup(html_text.replace("&nbsp;", " "), "html.parser")
        posts = {}
        for post in soup.select("ul.for-list li"):
            last_reply_time: str = post.select_one(".endreply a").get_text()
            if "-" in last_reply_time:  # date
                month, day = (int(time_str) for time_str in last_reply_time.split("-"))
                this_year = datetime.now().year
                last_reply_time = datetime(
                    year=this_year,
                    month=month,
                    day=day,
                    hour=23,
                    minute=59,
                    second=59,
                    microsecond=999999,
                    tzinfo=timezone("Asia/Shanghai"),
                )
            elif ":" in last_reply_time:  # time
                hour, minute = (
                    int(time_str) for time_str in last_reply_time.split(":")
                )
                now = datetime.now(tz=timezone("Asia/Shanghai"))
                last_reply_time = now.replace(
                    hour=hour, minute=minute, second=59, microsecond=999999
                )
            add_post = self.min_time is None or self.min_time < last_reply_time

            if add_post:
                post_anchor = post.select_one("a.truetit")
                post_id = post_anchor.get("href")[1:-5]
                post_url = f"{self.website_url}/{post_id}.html"
                post_title = post_anchor.get_text()
                posts[post_id] = {
                    "post_url": post_url,
                    "post_title": post_title,
                    "last_reply_time": last_reply_time.isoformat(),
                }
        return posts

    def get_floors(self, post_url: str) -> List:
        page = 1
        floor_contents = {}
        while True:
            page_url = post_url if page == 1 else post_url[:-5] + f"-{page}.html"
            try:
                html_text = (
                    self._requests_retry_session().get(page_url, timeout=10).text
                )
            except requests.exceptions.ConnectionError as e:
                print(e)
                print(page_url)
                continue
            soup = BeautifulSoup(html_text.replace("&nbsp;", " "), "html.parser")
            floors: bs4.element.ResultSet = soup.select("div.floor-show  ")

            if floors:
                for floor in floors:
                    floor_num = int(floor.select_one(".floornum").get("id"))
                    floor_content: BeautifulSoup = floor.select_one("td")
                    if floor_num == 0:
                        floor_content = floor_content.select_one(".quote-content")
                    quote = floor_content.select_one("blockquote")
                    if quote:
                        quote.clear()
                    floor_content_text: str = floor_content.get_text()
                    floor_content_text = re.sub(
                        r"(发自虎扑\w+客户端|\n|\u200b|\xa0)", "", floor_content_text
                    )
                    floor_time = datetime.strptime(
                        floor.select_one(".stime").get_text(), "%Y-%m-%d %H:%M"
                    )
                    floor_time = timezone("Asia/Shanghai").localize(floor_time)

                    add_floor_query = False
                    if self.queries is None:
                        add_floor_query = True
                    else:
                        for query in self.queries:
                            if query in floor_content_text:
                                add_floor_query = True
                    add_floor_time = self.min_time is None or self.min_time < floor_time

                    if add_floor_query and add_floor_time:
                        floor_username: str = floor.select_one(".j_u").get("uname")
                        floor_contents[floor_num] = {
                            "username": floor_username,
                            "content": floor_content_text,
                            "time": floor_time.isoformat(),
                        }
            else:  # empty page
                break
            page += 1

        return floor_contents

    def get_all_floors(self):
        posts = self.get_posts()
        if self.n_posts is not None:
            posts = {k: posts[k] for k in list(posts)[: self.n_posts]}
        post_ids = list(posts.keys())
        post_urls = [posts[post_id]["post_url"] for post_id in post_ids]
        pool = Pool(processes=10)
        floors_list = pool.map(self.get_floors, post_urls)
        post_details = {}
        for i in range(len(post_urls)):
            post_id = post_ids[i]
            floors = floors_list[i]
            if floors:
                post_details[post_id] = {}
                post_details[post_id]["meta"] = posts[post_id]
                post_details[post_id]["floors"] = floors
        return post_details


if __name__ == "__main__":
    start_time = datetime.now()

    read_post = ReadPost(
        queries=["瑞兹", "鳄鱼", "辛德拉", "卢锡安"], n_posts=10, min_time=None
    )  # timezone("UTC").localize(datetime.utcnow()) - timedelta(hours=1))

    print(json.dumps(read_post.get_all_floors(), ensure_ascii=False))
    print("Time:", datetime.now() - start_time)
