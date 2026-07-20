import random
import string
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import requests

BASE_URL = "https://take-two-mobile.vercel.app/api"

EMAIL = "admin@taketwo.ph"
PASSWORD = "admin123"

THREADS = 100
REQUESTS = 10000

STATUSES = [
    "Cleaning Stage",
    "Drying Area",
    "Restoration",
    "Quality Control",
    "Packaging",
    "For Release",
]

BINS = [
    "A-01","A-02","A-03",
    "B-01","B-02","B-03","B-04",
    "C-01","C-02"
]

BRANDS = [
    "Nike","Adidas","Puma","Converse",
    "New Balance","Asics","Jordan"
]

MODELS = [
    "Air Force",
    "574",
    "UltraBoost",
    "Old Skool",
    "Gel Kayano",
]

SERVICES = [
    "Deep Cleaning",
    "Whitening",
    "Repaint",
    "Sole Reglue",
]

thread_local = threading.local()


def login():
    s = requests.Session()

    r = s.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": EMAIL,
            "password": PASSWORD
        }
    )

    r.raise_for_status()

    token = r.json()["token"]

    s.headers.update({
        "Authorization": f"Bearer {token}"
    })

    return s


def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = login()
    return thread_local.session


def random_shoe():
    return {
        "itemId": str(uuid.uuid4())[:8],
        "size": str(random.randint(6, 12)),
        "brand": random.choice(BRANDS),
        "model": random.choice(MODELS),
        "color": random.choice(["Black","White","Blue","Red"]),
        "services": random.sample(SERVICES, random.randint(1,3)),
        "additionalServices": [],
        "sponsored": False,
        "damages": [],
        "otherDamage": "",
        "totalItemPayment": random.randint(300,1500),
        "photos": {}
    }


def random_job():

    today = datetime.now()

    return {
        "customer": f"Customer {uuid.uuid4().hex[:6]}",
        "phone": "09" + "".join(random.choices(string.digits, k=9)),
        "email": f"{uuid.uuid4().hex[:8]}@gmail.com",
        "dateReceived": today.strftime("%Y-%m-%d"),
        "expectedRelease": (today + timedelta(days=random.randint(2,7))).strftime("%Y-%m-%d"),
        "shoes": [random_shoe() for _ in range(random.randint(1,3))],
        "bin": random.choice(BINS),
        "status": random.choice(STATUSES),
        "receiveUpdates": random.choice([True, False]),
        "totalPayment": random.randint(500,5000),
        "notes": "Stress Test",
        "assignedTo": "Admin",
        "branch": "Main Branch",
        "released": False,
        "signatureDataUrl": None,
        "discountCode": None,
        "discountName": None,
        "discountPercent": None,
        "discountAmount": None
    }


def worker(_):

    session = get_session()

    r = session.post(
        f"{BASE_URL}/jobs",
        json=random_job(),
        timeout=30
    )

    return r.status_code


def main():

    success = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=THREADS) as executor:

        futures = [executor.submit(worker, i) for i in range(REQUESTS)]

        for future in as_completed(futures):

            code = future.result()

            if code == 201:
                success += 1
            else:
                failed += 1
                print(code)

    print("=" * 50)
    print("SUCCESS:", success)
    print("FAILED :", failed)


if __name__ == "__main__":
    main()