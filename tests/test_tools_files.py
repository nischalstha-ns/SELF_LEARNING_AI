"""Tests for vena.tools.files — jail enforcement + file operations."""
import os
import tempfile
import unittest
import zipfile

from vena.tools import files
from vena.tools._jail import _resolve


class JailTest(unittest.TestCase):
    def test_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(PermissionError):
                _resolve([root], os.path.join(root, "..", "evil.txt"))
            with self.assertRaises(PermissionError):
                _resolve([root], "/etc/passwd")

    def test_inside_allowed(self):
        with tempfile.TemporaryDirectory() as root:
            p = _resolve([root], os.path.join(root, "sub", "f.txt"))
            self.assertTrue(p.startswith(os.path.realpath(root)))

    def test_symlink_escape_blocked(self):
        with tempfile.TemporaryDirectory() as root:
            outside = tempfile.mkdtemp()
            link = os.path.join(root, "link")
            try:
                os.symlink(outside, link)
            except OSError:
                self.skipTest("symlinks not supported")
            with self.assertRaises(PermissionError):
                _resolve([root], os.path.join(link, "x"))


class FilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.roots = [self.tmp.name]

    def tearDown(self):
        self.tmp.cleanup()

    def _w(self, name, content="hello"):
        p = os.path.join(self.tmp.name, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(content)
        return p

    def test_write_read_list(self):
        files.write_file(self.roots, "a.txt", "data")
        got = files.read_file(self.roots, "a.txt")
        self.assertEqual(got["content"], "data")
        lst = files.list_files(self.roots, "")
        self.assertIn("a.txt", [e["name"] for e in lst["entries"]])

    def test_write_no_overwrite(self):
        files.write_file(self.roots, "a.txt", "x")
        with self.assertRaises(FileExistsError):
            files.write_file(self.roots, "a.txt", "y")
        files.write_file(self.roots, "a.txt", "y", overwrite=True)
        self.assertEqual(files.read_file(self.roots, "a.txt")["content"], "y")

    def test_write_outside_jail(self):
        with self.assertRaises(PermissionError):
            files.write_file(self.roots, "../outside.txt", "x")

    def test_edit_once(self):
        self._w("e.txt", "foo bar foo")
        with self.assertRaises(ValueError):  # ambiguous
            files.edit_file(self.roots, "e.txt", "foo", "baz")
        files.edit_file(self.roots, "e.txt", "foo bar", "FOO BAR")
        self.assertIn("FOO BAR", files.read_file(self.roots, "e.txt")["content"])

    def test_edit_missing(self):
        self._w("e.txt", "abc")
        with self.assertRaises(ValueError):
            files.edit_file(self.roots, "e.txt", "zzz", "q")

    def test_move_rename(self):
        self._w("old.txt", "v")
        files.move_file(self.roots, "old.txt", "sub/new.txt")
        self.assertTrue(os.path.isfile(os.path.join(self.tmp.name, "sub", "new.txt")))
        files.rename_file(self.roots, "sub/new.txt", "sub/renamed.txt")
        self.assertTrue(os.path.isfile(os.path.join(self.tmp.name, "sub", "renamed.txt")))

    def test_search(self):
        self._w("s1.py", "def needle(): pass\n")
        self._w("s2.txt", "nothing here\n")
        res = files.search_files(self.roots, r"def\s+needle", glob="*.py")
        self.assertEqual(len(res["hits"]), 1)
        self.assertIn("s1.py", res["hits"][0]["file"])
        with self.assertRaises(ValueError):
            files.search_files(self.roots, r"([bad")

    def test_zip_unzip(self):
        self._w("z/a.txt", "A")
        self._w("z/b.txt", "B")
        files.zip_files(self.roots, ["z"], "out.zip")
        zp = os.path.join(self.tmp.name, "out.zip")
        self.assertTrue(zipfile.is_zipfile(zp))
        files.unzip_file(self.roots, "out.zip", "restored")
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp.name, "restored", "z", "a.txt")))

    def test_zip_slip_blocked(self):
        zp = os.path.join(self.tmp.name, "evil.zip")
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr("../../evil.txt", "pwned")
        with self.assertRaises(ValueError):
            files.unzip_file(self.roots, "evil.zip", "dest")

    def test_specs(self):
        specs = files.make_specs(self.roots)
        names = {s.name for s in specs}
        self.assertTrue({"list_files", "read_file", "write_file", "edit_file",
                         "move_file", "search_files", "zip_files",
                         "unzip_file"} <= names)
        perms = {s.name: s.default_permission.value for s in specs}
        self.assertEqual(perms["read_file"], "observe")
        self.assertEqual(perms["write_file"], "execute")


if __name__ == "__main__":
    unittest.main()
