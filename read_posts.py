import json
import re
from collections import OrderedDict
from datetime import datetime, timedelta
import logging
from multiprocessing.pool import Pool
from typing import Dict, List, Optional, Tuple, Union
from sys import argv

import bs4
import requests
from bs4 import BeautifulSoup
from fake_useragent import FakeUserAgent
from pytz import timezone
from urllib3.util.retry import Retry


class ReadPost:
    website_url = "http://bbs.hupu.com"
    sub_name_id_map = {
        "lol": "3441",
        "5032": "5032",  # LOL游戏专区
        "realmadrid": "2543",
        "bxj": "34",
    }
    user_agent = FakeUserAgent().random

    def __init__(
        self,
        sub_name: str,
        queries: Optional[List[str]] = None,
        sub_pages_to_read: int = 10,
        time_ago: Optional[timedelta] = None,
    ) -> None:
        self.sub_name = sub_name
        self.queries = queries
        self.sub_pages_to_read = sub_pages_to_read
        if time_ago is None:
            self.min_time = None
        else:
            self.min_time = timezone("UTC").localize(datetime.utcnow()) - time_ago
        with open("cookie.txt", encoding="utf-8") as f:
            self.cookie = f.read().encode("utf-8")
        self.session = self._requests_retry_session()
        # use old version of hupu
        self._try_catch_requests("https://bbs.hupu.com/api/v1/dest?id=1&type=CATEGORY")

    def _requests_retry_session(
        self,
        retries=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
    ) -> requests.Session():
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _try_catch_requests(self, url, *args):
        try:
            response = self.session.get(
                url,
                timeout=10,
                headers={
                    "user-agent": self.user_agent,
                    "cookie": self.cookie,
                },
            )
            return response
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logging.info(e)
            logging.info(url)
            return -1
        except Exception as e:
            logging.error(e)
            logging.error(e)
            return -1

    def _filter_strings(self, input: str, *args) -> str:
        return re.sub(rf"({'|'.join(args)})", "", input)

    def get_posts_from_sub_page(self, sub_page_url: str) -> Dict:
        response = self._try_catch_requests(sub_page_url)
        if response == -1:
            return []
        html_text = response.text

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
                post_title = re.sub(r"\n", "", post_title)
                pages = post.select_one("span.multipage")
                n_pages = 1 if pages is None else int(pages.select("a")[-1].get_text())
                posts[post_id] = {
                    "sub": self.sub_name,
                    "sub_id": self.sub_name_id_map[self.sub_name],
                    "post_url": post_url,
                    "post_title": post_title,
                    "n_pages": n_pages,
                    "last_reply_time": last_reply_time.isoformat(),
                }
        return posts

    def get_all_posts(self) -> Dict:
        sub_url = f"{self.website_url}/{self.sub_name}"
        sub_page_urls = [
            f"{sub_url}-{sub_page}" for sub_page in range(1, self.sub_pages_to_read + 1)
        ]
        posts = {}
        pool = Pool(processes=20)
        posts_from_sub_page_list = pool.map(self.get_posts_from_sub_page, sub_page_urls)
        for posts_from_sub_page in posts_from_sub_page_list:
            posts |= posts_from_sub_page
        return posts

    def get_floors_for_page(self, page_url: str) -> Tuple[Union[Dict, bool]]:
        response = self._try_catch_requests(page_url)
        if response == -1:
            return [], True
        html_text = response.text

        floor_contents = {}
        soup = BeautifulSoup(html_text.replace("&nbsp;", " "), "html.parser")
        floors: bs4.element.ResultSet = soup.select("div.floor-show  ")
        if not floors:
            return [], True
        else:
            for floor in floors[::-1]:
                floor_anchor: BeautifulSoup = floor.select_one(".floornum")
                floor_num = int(floor_anchor.get("id"))
                floor_id: str = floor_anchor.get("href").split("#")[1]
                floor_url = f"{page_url}#{floor_id}"
                floor_content: BeautifulSoup = floor.select_one("td")
                if floor_num == 0:
                    floor_content = floor_content.select_one(".quote-content")
                quote = floor_content.select_one("blockquote")
                if quote:
                    quote.clear()
                floor_content_text: str = floor_content.get_text()
                strings_to_filter = [
                    "发自虎扑.+客户端",
                    "发自手机虎扑 m\.hupu\.com",
                    "\n",
                    "\r",
                    "\\",
                    "\u200b",
                    "\xa0",
                    "视频无法播放，浏览器版本过低，请升级浏览器或者使用其他浏览器",
                    "\[ 此帖被.+修改 \]",
                ]
                floor_content_text = self._filter_strings(
                    floor_content_text, *strings_to_filter
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
                        if query in floor_content_text.upper():
                            add_floor_query = True
                            break
                add_floor_time = self.min_time is None or self.min_time < floor_time

                if add_floor_query and add_floor_time:
                    floor_username: str = floor.select_one(".j_u").get("uname")
                    floor_contents[floor_num] = {
                        "floor_id": floor_id,
                        "floor_url": floor_url,
                        "username": floor_username,
                        "content": floor_content_text,
                        "time": floor_time.isoformat(),
                    }
                elif not add_floor_time:
                    break
        read_previous_page = add_floor_time  # if False, don't read previous page
        return floor_contents, read_previous_page

    def get_floors_for_post(self, post_url: str, n_pages: int) -> Dict:
        floor_contents = {}
        for page in range(n_pages, 0, -1):
            page_url = post_url if page == 1 else post_url[:-5] + f"-{page}.html"
            floor_for_page, read_previous_page = self.get_floors_for_page(page_url)
            floor_contents |= floor_for_page
            if not read_previous_page:
                break
        return OrderedDict(sorted(floor_contents.items()))

    def get_all_floors(self) -> Dict:
        posts = self.get_all_posts()
        post_ids = list(posts.keys())
        args = [
            (posts[post_id]["post_url"], posts[post_id]["n_pages"])
            for post_id in post_ids
        ]
        pool = Pool(processes=20)
        floors_list = pool.starmap(self.get_floors_for_post, args)
        all_floors = {}
        for i in range(len(post_ids)):
            post_id = post_ids[i]
            floors = floors_list[i]
            if floors:
                all_floors[post_id] = {}
                all_floors[post_id]["meta"] = posts[post_id]
                all_floors[post_id]["floors"] = floors
        return OrderedDict(sorted(all_floors.items()))

    def read_and_save(self):
        result = self.get_all_floors()
        with open(f"data/{self.sub_name}/floors.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(result, indent=4, ensure_ascii=False))


def read_posts(sub_name, sub_pages_to_read, time_ago, reply_type="keyword"):
    if reply_type == "keyword":
        with open(f"data/{sub_name}/input/keyword_reply.json", encoding="utf-8") as f:
            queries = json.loads(f.read()).keys()
            queries = [*queries]
    elif reply_type == "licking_dog":
        queries = ["#舔狗日记#"]
    start_time = datetime.now()
    read_post = ReadPost(
        sub_name=sub_name,
        queries=queries,
        sub_pages_to_read=sub_pages_to_read,
        time_ago=time_ago,
    )
    result = read_post.read_and_save()
    print("Time:", datetime.now() - start_time)
    return result


if __name__ == "__main__":
    if len(argv) == 1:
        sub_name = "bxj"
    else:
        sub_name = argv[1]
    result = read_posts(
        sub_name=sub_name,
        sub_pages_to_read=5,
        time_ago=timedelta(hours=12),
        reply_type="licking_dog",
    )
