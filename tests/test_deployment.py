import importlib.util
from pathlib import Path
import tempfile
import unittest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("wrapper", ROOT / "app.py")
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)


class DeploymentTests(unittest.TestCase):
    def test_navigation_source_to_built_bundle(self):
        import subprocess
        result = subprocess.run(
            ["node", "tests/navigation.mjs"], cwd=ROOT,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("srcdoc SecurityError reproduced and avoided", result.stdout)

    def test_full_bundle_and_dependencies(self):
        html, external = wrapper.load_frontend()
        self.assertEqual(external, [])
        self.assertIn("installLanding();", html)
        self.assertIn("SOCIAL_ROWS", html)
        self.assertIn("storyBefore", html)
        self.assertIn("storyAfter", html)
        self.assertNotIn('<script src=', html)
        self.assertNotIn('<link rel="stylesheet"', html)

    def test_relative_dependency_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "index.html"
            path.write_text('<html><body id="landingPage"><div id="dashboardShell"></div><script src="a.js"></script></body></html>')
            with self.assertRaisesRegex(ValueError, "相对路径"):
                wrapper.load_frontend(path)

    def test_missing_bundle(self):
        with self.assertRaises(FileNotFoundError):
            wrapper.load_frontend(ROOT / "missing-bundle.html")

    def test_streamlit_renders_complete_srcdoc(self):
        at = AppTest.from_file(str(ROOT / "app.py")).run()
        self.assertEqual(len(at.exception), 0)
        iframe = at.get("iframe")
        self.assertEqual(len(iframe), 1)
        self.assertEqual(iframe[0].proto.srcdoc, wrapper.DIST.read_text(encoding="utf-8"))
        self.assertTrue(iframe[0].proto.scrolling)
        self.assertIn("100dvh", at.markdown[0].value)


if __name__ == "__main__":
    unittest.main()
