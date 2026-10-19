"""Tests for vena.tools.browser — URL validation, no network needed."""
import unittest

from vena.tools import browser


class BrowserTest(unittest.TestCase):
    def test_check_url_rejects_non_http(self):
        for bad in ("file:///etc/passwd", "javascript:alert(1)", "ftp://x/y",
                    "notaurl"):
            with self.assertRaises(ValueError):
                browser._check_url(bad)

    def test_check_url_accepts(self):
        self.assertTrue(browser._check_url("https://example.com").startswith("https"))

    def test_clean_strips_tags(self):
        out = browser._clean("<html><body><h1>Hi</h1><script>x()</script><p>yo</p>")
        self.assertIn("Hi", out)
        self.assertIn("yo", out)
        self.assertNotIn("<h1>", out)
        self.assertNotIn("x()", out)

    def test_clean_unescapes(self):
        self.assertIn("&", browser._clean("a &amp; b"))

    def test_web_search_empty_query(self):
        with self.assertRaises(ValueError):
            browser.web_search("  ")

    def test_specs(self):
        specs = browser.make_specs()
        perms = {s.name: s.default_permission.value for s in specs}
        self.assertEqual(perms["web_search"], "observe")
        self.assertEqual(perms["read_page"], "observe")
        self.assertEqual(perms["open_url"], "execute")


if __name__ == "__main__":
    unittest.main()
