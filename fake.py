import json
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)  # reproducible runs

# ---------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------

LAPTOP_MODELS = [
    "AeroBook Pro 14",
    "AeroBook Air 13",
    "TitanForce 15 Gaming",
    "NimbusPad 2-in-1",
    "WorkHorse EliteBook X",
    "TravelLite 12",
]

COMPONENTS = [
    ("Motherboard", "MB"),
    ("Display Panel", "DSP"),
    ("Battery", "BAT"),
    ("SSD Storage", "SSD"),
    ("RAM Module", "RAM"),
    ("Keyboard Assembly", "KB"),
    ("Cooling Fan", "FAN"),
    ("Webcam Module", "CAM"),
]

MANUFACTURERS = ["Foxlink Corp", "Delta Electronics", "Wistron", "Quanta Computer", "Pegatron"]

CONDITIONS = ["New", "Open Box", "Used - Excellent", "Used - Good", "Used - Fair", "For Parts/Not Working"]

# Free-text condition blurbs a real eBay scrape would surface (messy on purpose)
CONDITION_NOTES = [
    "Barely used, works great! Minor scuff on lid.",
    "SCREEN HAS DEAD PIXEL - sold as is, no returns",
    "Tested and fully functional, battery holds charge ~4hrs",
    "Missing charger, otherwise good condition",
    "Cracked hinge but powers on fine",
    "Like new, opened for inspection only",
    "Keyboard sticky on a few keys, everything else works",
    "AS-IS FOR PARTS, board may be dead",
    "",  # some listings have no notes at all
]

SELLER_LOCATIONS = ["US", "CA", "UK", "DE", "IN", "AU", "SG"]


def make_sku(model: str, comp_code: str, idx: int) -> str:
    model_code = "".join(w[0] for w in model.split())[:4].upper()
    return f"{model_code}-{comp_code}-{idx:04d}"


# ---------------------------------------------------------------------
# 1. Internal BOM + Warranty dataset (structured, "clean")
# ---------------------------------------------------------------------

def generate_internal_bom_warranty(n_rows: int = 300):
    rows = []
    for i in range(1, n_rows + 1):
        model = random.choice(LAPTOP_MODELS)
        comp_name, comp_code = random.choice(COMPONENTS)
        sku = make_sku(model, comp_code, i)
        unit_cost = round(random.uniform(8, 220), 2)
        # Skew failure rates so Motherboard/Fan fail more -> supports the
        # "Circularity Score" use case in the doc
        base_failure = {
            "MB": 0.14, "FAN": 0.11, "BAT": 0.09, "KB": 0.06,
            "SSD": 0.04, "RAM": 0.03, "DSP": 0.02, "CAM": 0.02,
        }[comp_code]
        failure_rate = round(max(0.005, random.gauss(base_failure, 0.03)), 4)
        warranty_claims_90d = max(0, int(random.gauss(failure_rate * 500, 15)))
        units_shipped = random.randint(500, 20000)

        rows.append({
            "sku": sku,
            "laptop_model": model,
            "component_name": comp_name,
            "manufacturer": random.choice(MANUFACTURERS),
            "unit_cost_usd": unit_cost,
            "units_shipped": units_shipped,
            "warranty_claims_90d": warranty_claims_90d,
            "failure_rate": failure_rate,
            "warranty_period_months": random.choice([12, 24, 36]),
            "release_date": (datetime(2022, 1, 1) + timedelta(days=random.randint(0, 900))).strftime("%Y-%m-%d"),
        })
    return rows


# ---------------------------------------------------------------------
# 2. Scraped secondary-market listings (messy, "raw web data")
# ---------------------------------------------------------------------

def messy_title(model: str, condition: str) -> str:
    """Simulate inconsistent real-world eBay title formatting."""
    templates = [
        f"{model} Laptop {condition} - FAST SHIP",
        f"{model.upper()} - {condition} - L@@K!!",
        f"{model} ({condition}) Free Shipping",
        f"Genuine {model} {condition} Tested Working",
        f"{model.lower()} {condition.lower()} bundle w/ charger",
        f"** {model} ** {condition} ** SALE **",
    ]
    return random.choice(templates)


def generate_scraped_listings(n_rows: int = 500):
    listings = []
    for _ in range(n_rows):
        model = random.choice(LAPTOP_MODELS)
        condition = random.choice(CONDITIONS)
        base_price = {
            "New": random.uniform(700, 1400),
            "Open Box": random.uniform(550, 1100),
            "Used - Excellent": random.uniform(400, 900),
            "Used - Good": random.uniform(250, 650),
            "Used - Fair": random.uniform(120, 400),
            "For Parts/Not Working": random.uniform(30, 150),
        }[condition]
        price = round(base_price * random.uniform(0.85, 1.15), 2)

        listing = {
            "listing_id": str(uuid.uuid4())[:12],
            # intentionally messy / inconsistent title text -> needs
            # PySpark fuzzy-matching to map back to internal SKUs
            "title": messy_title(model, condition),
            "price_raw": f"${price:,.2f}",  # string, not numeric -> needs cleaning
            "condition": condition,
            "condition_notes": random.choice(CONDITION_NOTES),
            "seller_rating_pct": round(random.uniform(85.0, 100.0), 1) if random.random() > 0.05 else None,
            "seller_location": random.choice(SELLER_LOCATIONS),
            "shipping_cost_usd": round(random.choice([0, 0, 0, 4.99, 9.99, 14.99]), 2),
            "bids": random.randint(0, 25) if random.random() > 0.4 else None,
            "listed_date": (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 550))).strftime("%Y-%m-%dT%H:%M:%S"),
            "watchers": random.randint(0, 60),
        }

        # ~8% of listings missing the price field entirely (dirty web data)
        if random.random() < 0.08:
            listing.pop("price_raw")

        listings.append(listing)
    return listings


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import pandas as pd

    bom_rows = generate_internal_bom_warranty(300)
    listings_rows = generate_scraped_listings(500)

    # Structured internal data -> CSV (clean, typed)
    bom_df = pd.DataFrame(bom_rows)
    bom_df.to_csv("internal_bom_warranty.csv", index=False)

    # Scraped web data -> JSON lines (mirrors how a Scrapy pipeline
    # would dump raw items before landing in the Delta Lake Bronze layer)
    with open("scraped_ebay_listings.json", "w") as f:
        for item in listings_rows:
            f.write(json.dumps(item) + "\n")

    print(f"Generated {len(bom_df)} BOM/warranty rows -> internal_bom_warranty.csv")
    print(f"Generated {len(listings_rows)} scraped listings -> scraped_ebay_listings.json")
