import requests


def save_html(url):
    html_text = requests.get(url).text
    with open("test.html", "w", encoding="utf-8") as f:
        f.write(html_text)


save_html("https://bbs.hupu.com/lol")
