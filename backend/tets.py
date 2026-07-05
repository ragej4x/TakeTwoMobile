"""
Quick manual test: logs in, creates a discount code, then validates it.

Edit the CONFIG block below, then run:
    pip install requests
    python test_discount.py
"""

import sys
from datetime import datetime, timedelta

import requests

# ─── CONFIG ─────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000/api"   # your local FastAPI base URL
EMAIL = "admin@taketwo.ph"                # an existing account in `accounts`
PASSWORD = "admin123"

DISCOUNT_NAME = "WelcomeTakeTwoCavite!"
DISCOUNT_CODE = "WCT2C!"
DISCOUNT_PERCENT = 30
DISCOUNT_MAX_USES = 100                    # or None for unlimited
DISCOUNT_EXPIRES_IN_DAYS = 180             # or None for no expiration
# ────────────────────────────────────────────────────────────────────────────


def main() -> None:
    session = requests.Session()

    # 1. Log in
    print(f"Logging in as {EMAIL} ...")
    resp = session.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if not resp.ok:
        print(f"Login failed ({resp.status_code}): {resp.text}")
        sys.exit(1)

    token = resp.json()["token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("Logged in OK.\n")

    # 2. Create the discount
    expires_at = None
    if DISCOUNT_EXPIRES_IN_DAYS is not None:
        expires_at = (datetime.utcnow() + timedelta(days=DISCOUNT_EXPIRES_IN_DAYS)).isoformat()

    payload = {
        "name": DISCOUNT_NAME,
        "code": DISCOUNT_CODE,
        "percent": DISCOUNT_PERCENT,
        "maxUses": DISCOUNT_MAX_USES,
        "expiresAt": expires_at,
    }

    print(f"Creating discount: {payload}")
    resp = session.post(f"{BASE_URL}/discounts", json=payload)
    if resp.status_code == 409:
        print(f"Discount code {DISCOUNT_CODE} already exists — skipping creation, will validate it below.")
    elif not resp.ok:
        print(f"Create failed ({resp.status_code}): {resp.text}")
        sys.exit(1)
    else:
        print("Created:", resp.json(), "\n")

    # 3. List discounts (sanity check it's really there)
    resp = session.get(f"{BASE_URL}/discounts")
    resp.raise_for_status()
    print(f"Discounts on file ({len(resp.json())}):")
    for d in resp.json():
        print(" -", d)
    print()

    # 4. Validate the code, as the Add Entry screen would
    resp = session.post(f"{BASE_URL}/discounts/validate", json={"code": DISCOUNT_CODE})
    resp.raise_for_status()
    result = resp.json()
    print("Validation result:", result)

    if result["valid"]:
        print(f"\n✅ Code {DISCOUNT_CODE} is valid — {result['percent']}% off ({result['name']}).")
    else:
        print(f"\n❌ Code {DISCOUNT_CODE} is NOT valid: {result['message']}")


if __name__ == "__main__":
    main()