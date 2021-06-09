import asyncio
import json
import logging
from random import choice
from sys import argv
from typing import List

import requests
import urllib3
from fake_useragent import UserAgent

from exceptions import AccountBannedException, PostsDeletedException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SendPost:
    post_url = "https://bbs.hupu.com/post.php?action=reply"
    user_agent = UserAgent().random
    session = requests.Session()
    signature = '本回复由<a href="https://bbs.hupu.com/43452253.html">虎扑非官方机器人</a>自动发送。如果你对这个回复有什么问题或建议，请回复或私信。'

    def __init__(self, sub_name: str, queries: List[str], reply_type: str):
        self.sub_name = sub_name
        self.queries = queries
        self.reply_type = reply_type
        self.cookie = self._get_cookie()
        self.headers = self._get_headers()
        self.deleted_post_ids = []
        self.banned_sub_ids = []
        self.do_not_reply_users = self.get_do_not_reply_users()
        self.previously_replied_floors = self.get_previously_replied_floors()
        self.recently_replied_floors = []

    @staticmethod
    def _get_cookie():
        with open("cookie.txt", "r", encoding="utf-8") as f:
            return f.read()

    def _get_headers(self):
        return {
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": self.user_agent,
            "cookie": self.cookie,
            "charset": "utf-8",
        }

    def get_do_not_reply_users(self):
        with open("data/global/do_not_reply.json", encoding="utf-8") as f:
            return json.loads(f.read())["users"]

    def get_previously_replied_floors(self):
        try:
            with open(f"data/global/replied_floors.json", encoding="utf-8") as f:
                return json.loads(f.read())
        except (FileNotFoundError, ValueError):
            return []

    def get_stats_for_pairs(self, a, b):
        with open(f"data/{self.sub_name}/stats.json", encoding="utf-8") as f:
            stats = json.loads(f.read())
        return {
            stat_name: {a: stat[a], b: stat[b]} for stat_name, stat in stats.items()
        }

    @staticmethod
    def _get_comparison_pairs(query, content):
        content = content.replace(f"#{query}#", "").strip()
        a, b = content.split("vs", maxsplit=1)
        a, b = a.split(" ")[-1], b.split(" ")[0]
        return a, b

    @staticmethod
    def format_stats(stats):
        string_builder = []
        for stat_name, stat in stats.items():
            string_builder.append(f"{stat_name}:\n")
            for item, value in stat.items():
                string_builder.append(f"\t{item}: {value}\n")
        return "".join(string_builder)

    @staticmethod
    def format_newlines(input: str):
        return input.replace("\n", "<br/>")

    def get_comparison_reply_content(self, query: str, quote_content: str) -> str:
        try:
            pairs = self._get_comparison_pairs(query, quote_content)
            result = self.format_stats(self.get_stats_for_pairs(*pairs))
        except ValueError:
            result = "comparison not found"
        return result

    def get_keyword_reply_content(self, query: str) -> str:
        try:
            with open(
                f"data/{self.sub_name}/input/keyword_reply.json", encoding="utf-8"
            ) as f:
                keyword_mapper = json.loads(f.read())
                result = keyword_mapper[query]
                if (
                    type(result) == str
                    and result.startswith("%")
                    and result.endswith("%")
                ):
                    result = keyword_mapper[result.strip("%")]
                result = choice(result)
        except KeyError:
            result = "keyword not found"
        return result

    def get_licking_dog_reply_content(self, query: str) -> str:
        try:
            return self.session.get(
                "https://api.ixiaowai.cn/tgrj/index.php", verify=False
            ).text
        except requests.exceptions.RequestException:
            return "机器人出问题了，再试试吧？"

    def _get_reply_content(self, reply_type, **kw):
        reply_type_function_map = {
            "keyword": self.get_keyword_reply_content,
            "comparison": self.get_comparison_reply_content,
            "licking_dog": self.get_licking_dog_reply_content,
        }
        reply_type_args_map = {
            "keyword": ["query"],
            "comparison": ["query", "quote_content"],
            "licking_dog": ["query"],
        }
        reply_type_function = reply_type_function_map[reply_type]
        reply_type_kwargs: List = {
            arg: kw[arg] for arg in reply_type_args_map[reply_type]
        }
        return reply_type_function(**reply_type_kwargs)

    def get_replies_metadata(self, queries, reply_type):
        with open(f"data/{self.sub_name}/floors.json", encoding="utf-8") as f:
            floors_to_reply = json.loads(f.read())
        reply_metadata = []
        for post_id, post in floors_to_reply.items():
            sub_id = post["meta"]["sub_id"]
            floors = post["floors"]
            for floor in floors.values():
                if (
                    floor["username"] in self.do_not_reply_users
                    or {"post_id": post_id, "floor_id": floor["floor_id"]}
                    in self.previously_replied_floors
                ):
                    continue
                floor_id = floor["floor_id"]
                quote_content = floor["content"]
                for query in queries:
                    if query in quote_content:
                        content = self._get_reply_content(
                            reply_type,
                            query=query,
                            quote_content=quote_content,
                        )
                        reply_metadata.append(
                            {
                                "quote_floor_id": floor_id,
                                "content": f"{content}\n\n{self.signature}",
                                "sub_id": sub_id,
                                "post_id": post_id,
                            }
                        )
        return reply_metadata

    def get_all_replies(self):
        replies = self.get_replies_metadata(self.queries, self.reply_type)
        with open(f"data/{self.sub_name}/replies.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(replies, indent=4, ensure_ascii=False))
        return replies

    def mark_replied_floors(self):
        with open(f"data/global/replied_floors.json", "w", encoding="utf-8") as f:
            replied_floors = self.previously_replied_floors + [
                floor
                for floor in self.recently_replied_floors
                if floor not in self.previously_replied_floors
            ]
            f.write(json.dumps(replied_floors, indent=4, ensure_ascii=False))

    def test_account_banned(self, sub_id, post_id):
        response = requests.get(
            f"https://bbs.hupu.com/post.php?fid={sub_id}&tid={post_id}",
            headers=self.headers,
            timeout=10,
        )
        if "您在该板块封禁中" in response.text:
            raise AccountBannedException("Account banned")

    async def try_replying(self, url, headers, payload, times=1):
        try:
            response = requests.post(
                url,
                headers=headers,
                data=payload,
                timeout=10,
            )
            if "页面不存在" in response.text:
                raise PostsDeletedException()
            if "出错" in response.text:
                # doesn't actually post something
                self.test_account_banned(sub_id=payload["fid"], post_id=payload["tid"])
                raise requests.exceptions.HTTPError("嗯，出错了。")
            response.raise_for_status()
        except (requests.exceptions.HTTPError, requests.exceptions.ReadTimeout) as e:
            logging.info(e)
            await asyncio.sleep(3)
            if times < 3:
                return asyncio.create_task(
                    self.try_replying(url, headers, payload, times=times + 1)
                )
            else:
                return -1
        else:
            replied_floor = {
                "post_id": payload["tid"],
                "floor_id": payload["quotepid"],
            }
            print(f"Success! {replied_floor}")
            logging.info(f"Success! {replied_floor}")
            self.recently_replied_floors.append(replied_floor)
            return response

    async def send_reply(self, metadata):
        post_id = metadata["post_id"]
        sub_id = metadata["sub_id"]
        if sub_id in self.banned_sub_ids or post_id in self.deleted_post_ids:
            return -1
        quote_floor_id = metadata["quote_floor_id"]
        content = metadata["content"]
        payload = {
            "atc_content": self.format_newlines(content),
            "step": 2,
            "action": "reply",
            "fid": sub_id,
            "tid": post_id,
            "atc_html": 1,
        }
        if quote_floor_id != "tpc":  # it's not OP who sent it.
            payload["quotepid"] = quote_floor_id

        try:
            return await self.try_replying(self.post_url, self.headers, payload)
        except PostsDeletedException:
            logging.error(f"Deleted:{post_id}")
            self.deleted_post_ids.append(post_id)
        except AccountBannedException:
            logging.error(f"Banned:{sub_id}")
            self.banned_sub_ids.append(sub_id)

    async def send_all_replies(self, debug=False):
        replies = self.get_all_replies()
        if not debug:
            tasks = []
            for reply in replies:
                tasks.append(asyncio.create_task(self.send_reply(reply)))
            for task in tasks:
                await task
            self.mark_replied_floors()


async def send_posts(sub_name, reply_type, debug):
    if reply_type == "keyword":
        with open(f"data/{sub_name}/input/keyword_reply.json", encoding="utf-8") as f:
            queries = json.loads(f.read()).keys()
    elif reply_type == "licking_dog":
        queries = ["#舔狗日记#"]
    send_post = SendPost(sub_name, queries=queries, reply_type=reply_type)
    send_post.get_all_replies()
    task = asyncio.create_task(send_post.send_all_replies(debug))
    await task


if __name__ == "__main__":
    if len(argv) == 1:
        sub_name = "bxj"
    else:
        sub_name = argv[1]
    asyncio.run(send_posts(sub_name, reply_type="licking_dog", debug=True))
