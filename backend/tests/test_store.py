"""
Store tests: server-side pricing, stock, orders, invoices, access control, AI agent.
Run from the backend folder:
    python -m unittest tests.test_store -v
Uses a temporary database; never touches mhardware.db.
"""
import os
import shutil
import sys
import tempfile
import unittest

TMP = tempfile.mkdtemp(prefix="mh_store_")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(TMP, "test.db").replace("\\", "/")
os.environ["IMAGE_PROVIDER"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app                      # noqa: E402
from database.db import db                      # noqa: E402
from models import Category, Product, User      # noqa: E402

app = create_app()


def setUpModule():
    with app.app_context():
        cat = Category(name="Sanitary", slug="sanitary")
        db.session.add(cat)
        db.session.flush()
        db.session.add_all([
            Product(name="Basin Mixer Tap", slug="basin-mixer-tap", category_id=cat.id, price=1450,
                    discount_price=1290, stock=10, sku="T-1", unit="piece", availability=True),
            Product(name="Pillar Tap", slug="pillar-tap", category_id=cat.id, price=520, stock=5, availability=True),
            Product(name="Cement Bag 50 kg", slug="cement-bag", price=410, stock=100, unit="bag", availability=True),
            Product(name="Wash Basin", slug="wash-basin", category_id=cat.id, price=2450, stock=0, availability=True),
        ])
        admin = User(username="admin", is_admin=True)
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def pid(slug):
    with app.app_context():
        return Product.query.filter_by(slug=slug).first().id


def stock(slug):
    with app.app_context():
        return Product.query.filter_by(slug=slug).first().stock


ORDER = {"name": "Test Buyer", "phone": "9000000001", "address": "12 Test Street", "city": "Bhopal",
         "pincode": "462001", "order_type": "delivery", "payment_method": "cod"}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def order(self, slug, qty, **extra):
        return self.c.post("/api/orders", json={**ORDER, **extra,
                                                "items": [{"product_id": pid(slug), "quantity": qty, "price": 1}]})

    def test_quote_uses_server_prices(self):
        q = self.c.post("/api/orders/quote", json={"items": [{"product_id": pid("basin-mixer-tap"), "quantity": 2, "price": 1}]}).get_json()["data"]
        self.assertEqual(q["lines"][0]["price"], 1290)
        self.assertEqual(q["subtotal"], 2900)
        self.assertEqual(q["discount"], 320)
        self.assertEqual(q["grand_total"], 2580)

    def test_order_invoice_and_stock(self):
        before = stock("pillar-tap")
        r = self.order("pillar-tap", 2, grand_total=1).get_json()
        self.assertTrue(r["success"], r)
        d = r["data"]
        self.assertEqual(d["grand_total"], 1040)
        self.assertRegex(d["order_number"], r"^ORD-\d{4}-\d{6}$")
        self.assertRegex(d["invoice_number"], r"^MHS-\d{4}-\d{6}$")
        self.assertEqual(stock("pillar-tap"), before - 2)
        second = self.order("pillar-tap", 1).get_json()["data"]
        self.assertNotEqual(second["invoice_number"], d["invoice_number"])
        # guest token access
        self.assertEqual(self.c.get(f"/api/orders/view/{d['order_number']}").status_code, 404)
        self.assertEqual(self.c.get(f"/api/orders/view/{d['order_number']}?t={d['access_token']}").status_code, 200)
        pdf = self.c.get(f"/invoice/{d['invoice_number']}/pdf?t={d['access_token']}")
        self.assertEqual(pdf.data[:4], b"%PDF")
        # cancel restocks
        mid = stock("pillar-tap")
        self.c.post(f"/api/orders/{second['order_number']}/cancel", json={"token": second["access_token"]})
        self.assertEqual(stock("pillar-tap"), mid + 1)

    def test_rejections(self):
        self.assertFalse(self.order("wash-basin", 1).get_json()["success"])           # out of stock
        self.assertFalse(self.order("cement-bag", 101).get_json()["success"])         # more than stock
        self.assertFalse(self.order("cement-bag", -1).get_json()["success"])          # negative qty
        self.assertFalse(self.order("cement-bag", 1, payment_method="online").get_json()["success"])
        self.assertFalse(self.order("cement-bag", 1, pincode="12").get_json()["success"])
        self.assertTrue(self.order("cement-bag", 1, order_type="pickup", address="", pincode="").get_json()["success"])

    def test_customer_sees_only_own_orders(self):
        c = app.test_client()
        r = c.post("/api/account/register", json={"name": "Asha", "phone": "9000000099", "password": "secret123"})
        self.assertTrue(r.get_json()["success"])
        c.post("/api/orders", json={**ORDER, "phone": "9000000099", "items": [{"product_id": pid("cement-bag"), "quantity": 1}]})
        self.assertEqual(len(c.get("/api/account/orders").get_json()["data"]), 1)
        self.assertEqual(c.get("/api/orders").status_code, 401)                      # admin list

    def test_admin_status_flow(self):
        a = app.test_client()
        self.assertTrue(a.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).get_json()["success"])
        o = self.order("cement-bag", 1).get_json()["data"]
        self.assertTrue(a.put(f"/api/orders/{o['id']}", json={"status": "confirmed"}).get_json()["success"])
        self.assertFalse(a.put(f"/api/orders/{o['id']}", json={"status": "ready_for_pickup"}).get_json()["success"])
        hist = a.get(f"/api/orders/{o['id']}").get_json()["data"]["history"]
        self.assertEqual([h["status"] for h in hist], ["pending", "confirmed"])

    def test_ai_agent_proposes_but_never_acts(self):
        r = self.c.post("/api/ai/chat", json={"message": "I need 20 bags of cement"}).get_json()["data"]
        self.assertEqual(r["action"]["type"], "add_to_cart")
        self.assertEqual(r["action"]["quantity"], 20)
        r = self.c.post("/api/ai/chat", json={"message": "I need a tap under ₹1000"}).get_json()["data"]
        self.assertTrue(all(p["final_price"] <= 1000 for p in r["products"]))
        r = self.c.post("/api/ai/chat", json={"message": "xyzzy flux capacitor"}).get_json()["data"]
        self.assertEqual(r["products"], [])


if __name__ == "__main__":
    unittest.main()
