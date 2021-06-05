import re
from typing import List, Optional
import bs4
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from requests.sessions import session
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
from pytz import timezone
from multiprocessing import Pool
import json


class ReadPost:
    bbs_pages_to_read = 10
    website_url = "http://bbs.hupu.com"
    subs = ["lol", "5032"]  # LOL游戏专区

    def __init__(
        self,
        queries: Optional[List[str]] = None,
        n_posts: Optional[int] = None,
        time_ago: Optional[timedelta] = None,
    ) -> None:
        self.queries = queries
        self.n_posts = n_posts
        if time_ago is None:
            self.min_time = None
        else:
            self.min_time = timezone("UTC").localize(datetime.utcnow()) - time_ago
        self.session = self._requests_retry_session()
        # use old version of hupu
        self.session.get("https://bbs.hupu.com/api/v1/dest?id=1&type=CATEGORY")

    def _requests_retry_session(
        retries=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
    ):
        session = requests.Session()
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

    def get_posts_from_sub_page(self, sub_page_url: str) -> List:
        try:
            html_text = self.session.get(sub_page_url, timeout=10).text
            print("READING", sub_page_url)
        except requests.exceptions.ConnectionError as e:
            print(e)
            print(sub_page_url)
            return []
        except requests.exceptions.Timeout as e:
            print(e)
            print(sub_page_url)
            return []

        soup = BeautifulSoup(html_text.replace("&nbsp;", " "), "html.parser")
        posts = {}
        for post in soup.select("ul.for-list li"):
            last_reply_time: str = post.select_one(".endreply a").get_text()
            if "-" in last_reply_time:  # date
                date_split = [int(time_str) for time_str in last_reply_time.split("-")]
                if len(last_reply_time) > 5:  # 2020-01-01
                    year, month, day = date_split
                else:
                    year = timezone("Asia/Shanghai").localize(datetime.now()).year
                    month, day = date_split
                last_reply_time = datetime(
                    year=year,
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

    def get_all_posts(self) -> List:
        sub_urls = {sub: f"{self.website_url}/{sub}" for sub in self.subs}
        sub_page_urls = {}
        for sub, sub_url in sub_urls.items():
            sub_page_urls[sub] = [
                f"{sub_url}-{sub_page}"
                for sub_page in range(1, self.bbs_pages_to_read + 1)
            ]
        posts = {}
        for sub, sub_page_url_list in sub_page_urls.items():
            posts[sub] = sub
            posts["posts"] = {}
            for sub_page_url in sub_page_url_list:
                posts["sub"] = {sub}
                posts_from_sub_page = self.get_posts_from_sub_page(sub_page_url)
                posts["posts"] = posts_from_sub_page
        return posts

    def get_floors(self, post_url: str) -> List:
        page = 1
        floor_contents = {}
        n_pages = 1  # assumption. will update later.
        while True:
            if page > n_pages:
                break
            page_url = post_url if page == 1 else post_url[:-5] + f"-{page}.html"
            try:
                html_text = self.session.get(page_url, timeout=10).text
            except requests.exceptions.ConnectionError as e:
                print(e)
                print(page_url)
                continue
            except requests.exceptions.Timeout as e:
                print(e)
                print(page_url)
                continue
            print(page_url)

            soup = BeautifulSoup(html_text.replace("&nbsp;", " "), "html.parser")
            if page == 1:
                # regex find number of pages in JavaScript
                n_pages = int(re.findall(r"(?<=pageCount:)\b\w+\b", html_text)[0])

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
                        r"(发自虎扑\w+客户端|发自手机虎扑 m.hupu.com|\n|\u200b|\xa0|视频无法播放，浏览器版本过低，请升级浏览器或者使用其他浏览器)",
                        "",
                        floor_content_text,
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
                                break
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
        posts = self.get_all_posts()
        print("got all posts")
        if self.n_posts is not None:
            posts = {k: posts[k] for k in list(posts)[: self.n_posts]}
        post_ids = list(posts.keys())
        post_urls = [posts[post_id]["post_url"] for post_id in post_ids]
        pool = Pool(processes=10)
        floors_list = pool.map(self.get_floors, post_urls)
        post_details = {}
        for i in range(len(post_ids)):
            post_id = post_ids[i]
            floors = floors_list[i]
            if floors:
                post_details[post_id] = {}
                post_details[post_id]["meta"] = posts[post_id]
                post_details[post_id]["floors"] = floors
        return post_details


if __name__ == "__main__":
    with open("champion_alias.json", encoding="utf-8") as f:
        j = f.read()
        champions = json.loads(j)

    start_time = datetime.now()
    read_post = ReadPost(
        queries=[*champions.keys()],
        n_posts=10,
        time_ago=timedelta(days=1),
    )
    result = read_post.get_all_posts()
    print(result)
    print("Time:", datetime.now() - start_time)

    with open("view.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False))
