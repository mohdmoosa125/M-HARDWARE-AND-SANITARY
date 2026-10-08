"""
generate_images.py  -  Image Agent command line (run from the backend folder).

    python scripts/generate_images.py                    # default = --missing (safe)
    python scripts/generate_images.py --dry-run          # plan only, NO API calls
    python scripts/generate_images.py --limit 2
    python scripts/generate_images.py --id 42
    python scripts/generate_images.py --category tiles
    python scripts/generate_images.py --provider gemini
    python scripts/generate_images.py --regenerate --id 42
    python scripts/generate_images.py --all              # regenerate EVERY product (costs credits)
"""
import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app                      # noqa: E402
from database.migrate import ensure_columns     # noqa: E402
from services import image_generation as gen    # noqa: E402
from services import image_service as svc       # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="M Hardware product Image Agent")
    ap.add_argument("--missing", action="store_true", help="missing/fallback/failed images only (default)")
    ap.add_argument("--all", action="store_true", help="regenerate every product image")
    ap.add_argument("--id", type=int, help="single product id")
    ap.add_argument("--category", help="category slug or name")
    ap.add_argument("--limit", type=int, help="stop after N products")
    ap.add_argument("--dry-run", action="store_true", help="show the plan; make no API calls")
    ap.add_argument("--provider", help="force one provider: gemini|openai|stability|replicate")
    ap.add_argument("--regenerate", action="store_true", help="force a new image (use with --id)")
    ap.add_argument("--batch", type=int, default=5, help="pause 1 s after every N API products")
    a = ap.parse_args(argv)
    if a.regenerate and not a.id and not a.category:
        ap.error("--regenerate needs --id (or --category)")

    app = create_app()
    with app.app_context():
        ensure_columns()
        mode = "all" if a.all else "missing"
        force = a.all or a.regenerate
        products = svc.select_products(mode, product_id=a.id, category=a.category, limit=a.limit)
        chain = gen.usable_chain(a.provider)

        print(f"Providers configured: {', '.join(gen.configured_chain(a.provider)) or 'none'}")
        print(f"Providers usable    : {', '.join(chain) or 'none (no API calls will be made)'}")
        print(f"Products selected   : {len(products)}")

        if a.dry_run:
            for p in products:
                plan = svc.plan_product(p, force=force, provider=a.provider)
                print(f"\n#{plan['id']}  {plan['name']}   [{plan['category']}]")
                print(f"   status   : {plan['status']} ({plan['reason']})")
                print(f"   provider : {', '.join(plan['providers']) or '-'}")
                print(f"   reference: {plan['reference'] or '-'}")
                print(f"   action   : {plan['action']}   ({plan['operation']})")
                print(f"   prompt   : {plan['prompt']}")
            print("\nDry run only: nothing was generated or changed.")
            return 0

        if a.all and chain and not a.limit and not a.id:
            print(f"WARNING: --all will call {chain[0]} for up to {len(products)} products.")
        try:
            s = svc.run_batch(products, force=force, provider=a.provider, batch=a.batch)
        except KeyboardInterrupt:
            print("\nInterrupted. Finished products are saved; the rest were left untouched.")
            return 130

        print("\n" + "=" * 50)
        print("IMAGE GENERATION REPORT")
        print("=" * 50)
        print(f"Total     : {s['total']}")
        print(f"Skipped   : {s['skip']}")
        print(f"Generated : {s['generated']}  (+ {s['reference']} from reference images)")
        print(f"Fallback  : {s['fallback']}")
        print(f"Failed    : {s['failed']}")
        print(f"Time      : {s['seconds']} s")
        return 0


if __name__ == "__main__":
    sys.exit(main())
