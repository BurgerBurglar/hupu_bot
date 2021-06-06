import requests
import json
from urllib.parse import quote
from fake_useragent import UserAgent
from multiprocessing import Pool


def _get_comparison_pairs(content, query):
    content = content.replace(f"#{query}#", "").strip()
    a, b = content.split("vs", maxsplit=1)
    a, b = a.split(" ")[-1], b.split(" ")[0]
    return a, b


def get_stats_for_pairs(a, b):
    with open("stats.json", encoding="utf-8") as f:
        stats = json.loads(f.read())
    return {stat_name: {a: stat[a], b: stat[b]} for stat_name, stat in stats.items()}


def format_stats(stats):
    string_builder = []
    for stat_name, stat in stats.items():
        string_builder.append(f"{stat_name}:\n")
        for item, value in stat.items():
            string_builder.append(f"\t{item}: {value}\n")
    return "".join(string_builder)


def get_reply_content(quote_content: str, query: str) -> str:
    return format_stats(
        get_stats_for_pairs(*_get_comparison_pairs(quote_content, query))
    )


class SendPost:
    post_url = "https://bbs.hupu.com/post.php?action=reply"
    user_agent = UserAgent().random
    session = requests.Session()

    def __init__(self, query):
        self.query = query
        self.cookie = self._get_cookie()
        self.headers = self._get_headers()

    def _get_cookie(self):
        with open("cookie.txt") as f:
            return f.read()

    def _get_headers(self):
        return {
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": self.user_agent,
            "cookie": self.cookie,
        }

    def get_replies_metadata(self, query):
        with open("view.json", encoding="utf-8") as f:
            floors_to_reply = json.loads(f.read())
        reply_metadata = []
        for post_id, post in floors_to_reply.items():
            sub_id = post["meta"]["sub_id"]
            floors = post["floors"]
            for floor in floors.values():
                floor_id = floor["floor_id"]
                quote_content = floor["content"]
                content = get_reply_content(quote_content, query)
                reply_metadata.append(
                    {
                        "quote_floor_id": floor_id,
                        "content": f"{content}发送自send_posts自动回复",
                        "sub_id": sub_id,
                        "post_id": post_id,
                    }
                )
        return reply_metadata

    def send_post(self, metadata):
        quote_floor_id = metadata["quote_floor_id"]
        content = metadata["content"]
        sub_id = metadata["sub_id"]
        post_id = metadata["post_id"]
        payload = {
            "quotepid": quote_floor_id,
            "atc_content": quote(content),
            "step": 2,
            "action": "reply",
            "fid": sub_id,
            "tid": post_id,
        }
        payload = "&".join([f"{key}={value}" for key, value in payload.items()])

        response = self.session.post(self.post_url, headers=self.headers, data=payload)
        try:
            if "出错" in response.text:
                raise requests.exceptions.HTTPError("嗯，出错了。")
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(e)
        else:
            print("Success:", self.user_agent)

    def send_all_post(self):
        pool = Pool(processes=20)
        replies = self.get_replies_metadata(self.query)
        pool.map(self.send_post, replies)


if __name__ == "__main__":
    send_post = SendPost(query="皇马")
    send_post.send_all_post()
