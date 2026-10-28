"""Build the site once and check the SEO-critical output of every page."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BASE = "https://yakup-gunduz.com"


class SiteBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=ROOT, check=True, capture_output=True, text=True)
        cls.pages = sorted(DIST.rglob("index.html"))

    def test_core_files_exist(self):
        for name in (
            "index.html",
            "en/index.html",
            "404.html",
            "en/404.html",
            "robots.txt",
            "sitemap.xml",
            "llms.txt",
            "llms-full.txt",
            "favicon.ico",
            "assets/img/yakup-gunduz-photo.jpg",
            "assets/img/yakup-gunduz-photo-720.webp",
            "assets/img/yakup-gunduz-photo-400.webp",
        ):
            self.assertTrue((DIST / name).is_file(), name)

    def test_every_page_has_seo_basics(self):
        self.assertGreaterEqual(len(self.pages), 10)
        for page in self.pages:
            src = page.read_text(encoding="utf-8")
            with self.subTest(page=str(page.relative_to(DIST))):
                self.assertEqual(src.count("<h1"), 1)
                self.assertRegex(src, r"<title>[^<]{10,}</title>")
                self.assertRegex(src, r'<meta name="description" content="[^"]{50,}"')
                self.assertRegex(src, rf'<link rel="canonical" href="{re.escape(BASE)}/[^"]*"')
                for lang in ("tr", "en", "x-default"):
                    self.assertIn(f'hreflang="{lang}"', src)
                self.assertIn('property="og:image"', src)
                self.assertIn(f'<meta name="thumbnail" content="{BASE}/assets/img/yakup-gunduz-photo.jpg">', src)
                self.assertIn(f'"@id":"{BASE}/#photo"', src)
                self.assertIn(f'"url":"{BASE}/assets/img/yakup-gunduz-photo.jpg"', src)
                self.assertIn('application/ld+json', src)

    def test_sitemap_lists_every_page(self):
        sitemap = (DIST / "sitemap.xml").read_text(encoding="utf-8")
        for page in self.pages:
            path = "/" + str(page.parent.relative_to(DIST)).replace(".", "").strip("/")
            url = BASE + (path.rstrip("/") + "/" if path != "/" else "/")
            self.assertIn(f"<loc>{url}</loc>", sitemap)
        self.assertIn(f"<image:loc>{BASE}/assets/img/yakup-gunduz-bust-1200.webp</image:loc>", sitemap)
        self.assertIn(f"<image:loc>{BASE}/assets/img/yakup-gunduz-photo.jpg</image:loc>", sitemap)
        self.assertIn(f"Sitemap: {BASE}/sitemap.xml", (DIST / "robots.txt").read_text(encoding="utf-8"))

    def test_no_previous_owner_or_article_leftovers(self):
        for path in DIST.rglob("*"):
            if path.suffix in (".html", ".txt", ".xml"):
                text = path.read_text(encoding="utf-8").lower()
                with self.subTest(path=str(path.relative_to(DIST))):
                    for word in ("kaahn", "kaan demir", "/yazilar/", "/en/articles/"):
                        self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
