import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from tools import build_feed
from tools.build_feed import parse_articles, render_feed


class FeedTests(unittest.TestCase):
    def test_extracts_two_lead_paragraphs_as_plain_text(self):
        html = "<article><p>第一段 <strong>重点</strong> &amp; 内容</p><p>第二段</p><p>忽略第三段</p></article>"
        parse_summary = getattr(build_feed, "parse_article_summary", lambda _html: None)

        self.assertEqual(parse_summary(html), "第一段 重点 & 内容 第二段")

    def test_summary_is_capped_at_500_characters(self):
        html = f"<article><p>{'甲' * 600}</p></article>"
        parse_summary = getattr(build_feed, "parse_article_summary", lambda _html: None)

        self.assertEqual(parse_summary(html), "甲" * 500)

    def test_missing_article_body_returns_no_summary(self):
        parse_summary = getattr(build_feed, "parse_article_summary", None)
        self.assertTrue(callable(parse_summary))

        self.assertIsNone(parse_summary("<article><p> </p></article>"))

    def test_extracts_unique_articles_and_publication_dates(self):
        html = """
        <div class="pdb10 real-article relative">
          <a class="eps" href="/news/china/202611/123.html" title="新闻一">新闻一</a>
          <div class="f12 mgt5 text-track">11月22日 20:20 · 焦点</div>
        </div>
        <div class="article relative mgb15 line-sm line">
          <a href="/news/world/202611/124.html" title="新闻二"><div class="m-eps">新闻二</div></a>
          <div class="f12 text-track pdt10">26年11月22日 19时10分11秒</div>
        </div>
        <div class="pdb10 real-article relative">
          <a href="/news/china/202611/123.html" title="新闻一">重复</a>
          <div class="f12 mgt5 text-track">11月22日 20:20 · 焦点</div>
        </div>
        <div><a href="/news/world/202611/125.html" title="新闻三">新闻三</a></div>
        <div><a href="/news/world/202611/126.html" title="新闻四">新闻四</a></div>
        <div><a href="/news/world/202611/127.html" title="新闻五">新闻五</a></div>
        """

        articles = parse_articles(html, datetime(2026, 11, 22, 21, 0))

        self.assertEqual(len(articles), 5)
        self.assertEqual(articles[0]["title"], "新闻一")
        self.assertEqual(articles[0]["link"], "https://www.zaochenbao.com/news/china/202611/123.html")
        self.assertEqual(articles[0]["published"].hour, 20)
        self.assertEqual(articles[1]["published"].second, 11)

    def test_rendered_feed_uses_short_brand_and_valid_rss(self):
        xml = render_feed([
            {
                "title": "新闻",
                "link": "https://www.zaochenbao.com/news/china/202611/123.html",
                "published": datetime(2026, 11, 22, 20, 20),
            }
        ])

        self.assertIn("<title>ZCB</title>", xml)
        self.assertIn("<item>", xml)
        self.assertNotIn("联合早报", xml)

    def test_rss_description_contains_escaped_summary(self):
        summary = "摘要 & <重点>"
        xml = render_feed([
            {
                "title": "新闻",
                "link": "https://www.zaochenbao.com/news/china/202611/123.html",
                "published": None,
                "summary": summary,
            },
            {
                "title": "无摘要新闻",
                "link": "https://www.zaochenbao.com/news/china/202611/124.html",
                "published": None,
                "summary": None,
            },
        ])
        items = ET.fromstring(xml).findall("./channel/item")

        self.assertEqual(items[0].findtext("description"), summary)
        self.assertIsNone(items[1].find("description"))

    def test_cached_summaries_avoid_refetch(self):
        enrich = getattr(build_feed, "enrich_articles", None)
        self.assertTrue(callable(enrich))
        calls = []
        article = {"title": "新闻", "link": "https://example.com/1"}

        result = enrich([article], {article["link"]: "缓存摘要"}, lambda url: calls.append(url))

        self.assertEqual(result[0]["summary"], "缓存摘要")
        self.assertEqual(calls, [])

    def test_uncached_article_gets_summary(self):
        enrich = getattr(build_feed, "enrich_articles", None)
        self.assertTrue(callable(enrich))
        article = {"title": "新闻", "link": "https://example.com/1"}

        result = enrich([article], {}, lambda _url: "新摘要")

        self.assertEqual(result[0]["summary"], "新摘要")

    def test_failed_article_fetch_preserves_item(self):
        enrich = getattr(build_feed, "enrich_articles", None)
        self.assertTrue(callable(enrich))
        article = {"title": "新闻", "link": "https://example.com/1"}

        def fail(_url):
            raise OSError("upstream unavailable")

        result = enrich([article], {}, fail)

        self.assertEqual(result[0]["title"], "新闻")
        self.assertEqual(result[0]["link"], article["link"])
        self.assertIsNone(result[0]["summary"])

    def test_load_cached_summaries_from_feed(self):
        load_cache = getattr(build_feed, "load_cached_summaries", None)
        self.assertTrue(callable(load_cache))
        link = "https://www.zaochenbao.com/news/china/202611/123.html"
        xml = render_feed([{"title": "新闻", "link": link, "published": None, "summary": "已缓存摘要"}])
        with TemporaryDirectory() as directory:
            path = Path(directory) / "feed.rss"
            path.write_text(xml, encoding="utf-8")

            self.assertEqual(load_cache(path), {link: "已缓存摘要"})

    def test_rejects_pages_without_news(self):
        with self.assertRaises(ValueError):
            parse_articles("<html><body>No articles</body></html>", datetime(2026, 11, 22))


if __name__ == "__main__":
    unittest.main()
