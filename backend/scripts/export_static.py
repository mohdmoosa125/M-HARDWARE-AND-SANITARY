"""
export_static.py
----------------
Snapshot the public catalogue (settings, categories, products, gallery) into
frontend/data/catalog.json and copy public images into frontend/uploads/, so the
frontend works on static hosting (Netlify) without the Flask backend.

Run from the project root after editing products in the admin panel:
    backend/venv/Scripts/python backend/scripts/export_static.py
"""
import json
import os
import shutil
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND)

from app import app  # noqa: E402

FRONTEND = os.path.join(BACKEND, "..", "frontend")
PUBLIC_UPLOADS = ("products", "categories", "gallery")


def get(client, path):
    res = client.get("/api" + path)
    body = res.get_json()
    if res.status_code != 200 or not body or not body.get("success"):
        raise SystemExit(f"Export failed on {path}: HTTP {res.status_code}")
    return body["data"]


def main():
    client = app.test_client()
    products, page = [], 1
    while True:
        res = client.get(f"/api/products?limit=100&page={page}&sort=newest").get_json()
        products += res["data"]
        if page >= res["meta"]["pages"]:
            break
        page += 1

    catalog = {
        "settings": get(client, "/settings"),
        "categories": get(client, "/categories"),
        "category_tree": get(client, "/categories?tree=1"),
        "filters": get(client, "/products/filters"),
        "products": products,
        "gallery": get(client, "/gallery"),
    }
    os.makedirs(os.path.join(FRONTEND, "data"), exist_ok=True)
    with open(os.path.join(FRONTEND, "data", "catalog.json"), "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(",", ":"))

    for sub in PUBLIC_UPLOADS:
        src = os.path.join(BACKEND, "uploads", sub)
        dst = os.path.join(FRONTEND, "uploads", sub)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)

    print(f"Exported {len(products)} products, {len(catalog['categories'])} categories, "
          f"{len(catalog['gallery'])} gallery images.")


if __name__ == "__main__":
    main()
