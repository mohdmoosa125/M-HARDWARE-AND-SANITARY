"""
Image Agent tests. Run from the backend folder:
    python -m unittest tests.test_image_agent -v
Uses a temporary database and uploads folder; no real API is ever called.
"""
import io
import os
import random
import shutil
import sys
import tempfile
import time
import unittest

TMP = tempfile.mkdtemp(prefix="mh_test_")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(TMP, "test.db").replace("\\", "/")
os.environ["REFERENCE_DIR"] = os.path.join(TMP, "uploads", "references")
for var in ("IMAGE_PROVIDER", "IMAGE_FALLBACK_PROVIDERS", "IMAGE_MODEL", "GEMINI_API_KEY",
            "OPENAI_API_KEY", "STABILITY_API_KEY", "REPLICATE_API_TOKEN"):
    os.environ[var] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw                                  # noqa: E402
from app import create_app                                        # noqa: E402
from database.db import db                                        # noqa: E402
from models import Category, Product                              # noqa: E402
from services import image_generation as gen                      # noqa: E402
from services import image_processor, image_service as svc        # noqa: E402
from services import image_validator, svg_fallback                # noqa: E402
from scripts import generate_images as cli                        # noqa: E402


def noisy_png(size=1024, seed=1):
    random.seed(seed)
    im = Image.new("RGB", (size, size), (244, 248, 251))
    d = ImageDraw.Draw(im)
    for _ in range(30):
        x, y = random.randint(50, size - 250), random.randint(50, size - 250)
        d.ellipse((x, y, x + random.randint(40, 200), y + random.randint(40, 200)),
                  fill=tuple(random.randint(0, 200) for _ in range(3)))
    px = im.load()
    for _ in range(size * 150):
        px[random.randrange(size), random.randrange(size)] = tuple(random.randrange(256) for _ in range(3))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = os.path.join(TMP, "uploads")
        for sub in ("products", "references"):
            os.makedirs(os.path.join(cls.root, sub), exist_ok=True)
        image_processor.UPLOADS = svg_fallback.UPLOADS = cls.root
        image_validator.BACKEND = svc.BACKEND = TMP
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()
        if not Category.query.filter_by(slug="taps").first():
            db.session.add(Category(name="Taps", slug="taps"))
            db.session.commit()
        cls.orig_adapters = dict(gen.ADAPTERS)

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def setUp(self):
        gen.ADAPTERS.clear()
        gen.ADAPTERS.update(self.orig_adapters)
        gen.reset_run_state()
        for var in ("IMAGE_PROVIDER", "IMAGE_FALLBACK_PROVIDERS", "GEMINI_API_KEY", "OPENAI_API_KEY"):
            os.environ[var] = ""
        self.calls = []

    def configure(self, primary, fallbacks=""):
        os.environ["IMAGE_PROVIDER"] = primary
        os.environ["IMAGE_FALLBACK_PROVIDERS"] = fallbacks
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        os.environ["OPENAI_API_KEY"] = "test-openai-key"

    def adapter(self, name, ok=True, error="boom"):
        def fn(prompt, negative, ref, model):
            self.calls.append(name)
            if not ok:
                raise gen.ProviderError(error)
            return noisy_png(1024, seed=len(self.calls) + hash(name) % 50)
        gen.ADAPTERS[name] = fn

    def product(self, name, image=None, **kw):
        p = Product(name=name, slug=name.lower().replace(" ", "-"), category_id=1, price=123.0,
                    stock=7, sku="SKU-" + name[:3].upper(), description="d", image=image, **kw)
        db.session.add(p)
        db.session.commit()
        return p

    def snapshot(self, p):
        return (p.name, p.sku, p.price, p.stock, p.category_id, p.description, p.brand)


class PipelineTests(Base):
    def test_existing_valid_image_is_skipped(self):
        path = os.path.join(self.root, "products", "valid-one.webp")
        Image.open(io.BytesIO(noisy_png(1200))).save(path, "WEBP")
        p = self.product("Valid One", image="/uploads/products/valid-one.webp")
        self.configure("gemini")
        self.adapter("gemini")
        self.assertEqual(svc.process_product_image(p, log=lambda m: None)["status"], "skip")
        self.assertEqual(self.calls, [])
        self.assertEqual(p.image_status, "ready")

    def test_missing_image_generated_and_db_updated(self):
        p = self.product("Chrome Angle Cock")
        before = self.snapshot(p)
        self.configure("gemini")
        self.adapter("gemini")
        res = svc.process_product_image(p, log=lambda m: None)
        self.assertEqual(res["status"], "generated", res)
        self.assertEqual(p.image, "/uploads/products/chrome-angle-cock.webp")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "products", "chrome-angle-cock.webp")))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "products", "chrome-angle-cock.jpg")))
        self.assertEqual(p.image_status, "ready")
        self.assertTrue(p.image_provider.startswith("gemini:"))
        with Image.open(os.path.join(self.root, "products", "chrome-angle-cock.webp")) as im:
            self.assertEqual(im.size, (1200, 1200))
        self.assertEqual(self.snapshot(p), before)          # nothing but image fields changed
        self.assertNotIn("\\", p.image)

    def test_broken_image_detected_and_regenerated(self):
        broken = os.path.join(self.root, "products", "broken-one.jpg")
        with open(broken, "wb") as f:
            f.write(b"this is not an image" * 200)
        p = self.product("Broken One", image="/uploads/products/broken-one.jpg")
        self.assertEqual(svc.evaluate(p)[0], "missing")
        self.configure("gemini")
        self.adapter("gemini")
        self.assertEqual(svc.process_product_image(p, log=lambda m: None)["status"], "generated")
        self.assertEqual(p.image, "/uploads/products/broken-one.webp")

    def test_reference_image_used_without_api(self):
        p = self.product("Ref Product")
        ref = os.path.join(self.root, "references", "ref-product.png")
        Image.open(io.BytesIO(noisy_png(900))).save(ref)
        self.configure("gemini")
        self.adapter("gemini")
        res = svc.process_product_image(p, log=lambda m: None)
        self.assertEqual(res["status"], "reference", res)
        self.assertEqual(self.calls, [])
        self.assertEqual(p.image_provider, "reference")

    def test_provider_failure_uses_configured_fallback(self):
        p = self.product("Fallback Provider Product")
        self.configure("gemini", "openai")
        self.adapter("gemini", ok=False)
        self.adapter("openai")
        res = svc.process_product_image(p, log=lambda m: None)
        self.assertEqual(res["status"], "generated")
        self.assertEqual(self.calls, ["gemini", "openai"])
        self.assertTrue(p.image_provider.startswith("openai:"))

    def test_unconfigured_provider_is_never_called(self):
        p = self.product("Cost Safe Product")
        self.configure("gemini")                  # openai has a key but is NOT in the chain
        self.adapter("gemini", ok=False)
        self.adapter("openai")
        svc.process_product_image(p, log=lambda m: None)
        self.assertEqual(self.calls, ["gemini"])

    def test_all_providers_fail_uses_svg_fallback(self):
        p = self.product("Doomed Product")
        self.configure("gemini", "openai")
        self.adapter("gemini", ok=False)
        self.adapter("openai", ok=False)
        res = svc.process_product_image(p, log=lambda m: None)
        self.assertEqual(res["status"], "fallback")
        self.assertEqual(p.image_status, "fallback")
        self.assertTrue(p.image.endswith(".svg"))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "products", "doomed-product.svg")))

    def test_missing_api_key_skips_provider(self):
        p = self.product("No Key Product")
        os.environ["IMAGE_PROVIDER"] = "gemini"
        os.environ["GEMINI_API_KEY"] = ""
        self.adapter("gemini")
        res = svc.process_product_image(p, log=lambda m: None)
        self.assertEqual(self.calls, [])
        self.assertEqual(res["status"], "fallback")

    def test_low_quality_output_tries_next_provider(self):
        p = self.product("Low Quality Product")
        self.configure("gemini", "openai")
        gen.ADAPTERS["gemini"] = lambda *a: (self.calls.append("gemini"), noisy_png(200))[1]
        self.adapter("openai")
        self.assertEqual(svc.process_product_image(p, log=lambda m: None)["status"], "generated")
        self.assertEqual(self.calls, ["gemini", "openai"])

    def test_dry_run_makes_no_api_call(self):
        self.product("Dry Run Product")
        self.configure("gemini")
        gen.ADAPTERS["gemini"] = lambda *a: self.fail("API called during dry run")
        self.assertEqual(cli.main(["--dry-run"]), 0)


class AdminTests(Base):
    def client(self, admin=True):
        c = self.app.test_client()
        if admin:
            with c.session_transaction() as s:
                s["admin_id"], s["admin_name"] = 1, "admin"
        return c

    def test_endpoints_require_admin(self):
        c = self.client(admin=False)
        self.assertEqual(c.get("/api/admin/images/report").status_code, 401)
        self.assertEqual(c.post("/api/admin/images/generate-missing").status_code, 401)

    def test_job_status_cancel_regenerate_and_manual_override(self):
        p1, p2 = self.product("Job One"), self.product("Job Two")
        self.configure("gemini")
        self.adapter("gemini")
        c = self.client()
        rep = c.get("/api/admin/images/report").get_json()["data"]
        self.assertGreaterEqual(rep["counts"]["missing"], 2)

        job = c.post("/api/admin/images/generate-missing", json={"limit": 50}).get_json()["data"]
        self.assertTrue(job["job_id"])
        for _ in range(60):
            st = c.get(f"/api/admin/images/status/{job['job_id']}").get_json()["data"]
            if st["state"] != "running":
                break
            time.sleep(0.5)
        self.assertEqual(st["state"], "done")
        self.assertEqual(st["processed"], st["total"])
        self.assertEqual(st["failed"], 0)
        db.session.expire_all()
        self.assertEqual(db.session.get(Product, p1.id).image_status, "ready")

        self.assertEqual(c.post("/api/admin/images/cancel/nope").status_code, 404)
        self.assertEqual(c.get("/api/admin/images/status/nope").status_code, 404)

        res = c.post(f"/api/admin/images/regenerate/{p2.id}").get_json()["data"]
        self.assertEqual(res["image_status"], "ready")

        # manual upload overrides the generated image
        put = c.put(f"/api/products/{p2.id}", json={"image": "/uploads/products/job-one.webp"})
        self.assertTrue(put.get_json()["success"])
        db.session.expire_all()
        self.assertEqual(db.session.get(Product, p2.id).image_provider, "manual")

    def test_new_product_without_image_is_missing(self):
        c = self.client()
        r = c.post("/api/products", json={"name": "Brand New Item", "price": 10})
        pid = r.get_json()["data"]["id"]
        self.assertEqual(db.session.get(Product, pid).image_status, "missing")


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
