import unittest
from datetime import datetime

from tools.build_feed import parse_articles, render_feed


class FeedTests(unittest.TestCase):
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

    def test_rejects_pages_without_news(self):
        with self.assertRaises(ValueError):
            parse_articles("<html><body>No articles</body></html>", datetime(2026, 11, 22))


if __name__ == "__main__":
    unittest.main()
