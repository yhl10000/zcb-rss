from datetime import datetime
from email.utils import format_datetime
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo


BASE_URL = "https://www.zaochenbao.com"
SOURCE_URL = BASE_URL + "/"
OUTPUT = Path(__file__).resolve().parents[1] / "zcb.rss"
SHANGHAI = ZoneInfo("Asia/Shanghai")


class Element:
    def __init__(self, tag, attrs, parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []

    def text(self):
        return " ".join(
            " ".join(child.split()) if isinstance(child, str) else child.text()
            for child in self.children
        ).strip()

    def find_all(self, tag):
        for child in self.children:
            if isinstance(child, Element):
                if child.tag == tag:
                    yield child
                yield from child.find_all(tag)


class PageParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("document", [])
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(element)
        if tag not in self.VOID:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Element(tag, attrs, self.stack[-1]))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _published(meta, url, now):
    exact = re.search(r"(\d{2,4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})时(\d{2})分(\d{2})秒", meta)
    if exact:
        year, month, day, hour, minute, second = map(int, exact.groups())
        return datetime(year + 2000 if year < 100 else year, month, day, hour, minute, second, tzinfo=SHANGHAI)

    short = re.search(r"(\d{1,2})月-?(\d{1,2})日\s*(\d{1,2}):(\d{2})", meta)
    if not short:
        return None
    month, day, hour, minute = map(int, short.groups())
    path_date = re.search(r"/news/[^/]+/(\d{4})(\d{2})/", url)
    year = int(path_date[1]) if path_date and int(path_date[2]) == month else now.year
    if year == now.year and (month, day) > (now.month, now.day):
        year -= 1
    return datetime(year, month, day, hour, minute, tzinfo=SHANGHAI)


def parse_articles(html, now=None):
    now = now or datetime.now(SHANGHAI)
    parser = PageParser()
    parser.feed(html)
    articles = {}
    for anchor in parser.root.find_all("a"):
        href = anchor.attrs.get("href", "")
        url = BASE_URL + href if href.startswith("/") else href
        if not re.fullmatch(r"https://www\.zaochenbao\.com/news/[^/]+/\d{6}/\d+\.html", url):
            continue
        title = " ".join(anchor.attrs.get("title", "").split()) or anchor.text()
        if not title:
            continue
        parent = anchor.parent
        meta = ""
        while parent:
            classes = set(parent.attrs.get("class", "").split())
            if parent.tag == "div" and classes.intersection({"real-article", "article"}):
                meta = parent.text()
                break
            parent = parent.parent
        published = _published(meta, url, now)
        previous = articles.get(url)
        if not previous or (published and not previous["published"]):
            articles[url] = {"title": title, "link": url, "published": published}
    if len(articles) < 5:
        raise ValueError(f"Expected at least 5 news articles, found {len(articles)}")
    return sorted(articles.values(), key=lambda item: item["published"] or datetime.min.replace(tzinfo=SHANGHAI), reverse=True)[:100]


def render_feed(articles):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    for tag, value in (("title", "ZCB"), ("link", SOURCE_URL), ("description", "ZCB 新闻更新"), ("language", "zh-cn")):
        ET.SubElement(channel, tag).text = value
    for article in articles:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = article["title"]
        ET.SubElement(item, "link").text = article["link"]
        ET.SubElement(item, "guid", isPermaLink="true").text = article["link"]
        if article["published"]:
            ET.SubElement(item, "pubDate").text = format_datetime(article["published"])
    ET.indent(rss)
    return ET.tostring(rss, encoding="unicode", xml_declaration=True)


def main():
    request = Request(SOURCE_URL, headers={"User-Agent": "ZCB-RSS/1.0 (scheduled RSS feed)"})
    with urlopen(request, timeout=20) as response:
        body = response.read()
        encoding = response.headers.get_content_charset() or "gbk"
    html = body.decode(encoding, errors="replace")
    feed = render_feed(parse_articles(html))
    temp = OUTPUT.with_suffix(".rss.tmp")
    temp.write_text(feed, encoding="utf-8")
    temp.replace(OUTPUT)
    print(f"Updated {OUTPUT.name} with {feed.count('<item>')} items")


if __name__ == "__main__":
    main()
