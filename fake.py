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

CONDITION_NOTES = [
    "Barely used, works great! Minor scuff on lid.",
    "SCREEN HAS DEAD PIXEL - sold as is, no returns",
    "Tested and fully functional, battery holds charge ~4hrs",
    "Missing charger, otherwise good condition",
    "Cracked hinge but powers on fine",
    "Like new, opened for inspection only",
    "Keyboard sticky on a few keys, everything else works",
    "AS-IS FOR PARTS, board may be dead",
    "",
]

SELLER_LOCATIONS = ["US", "CA", "UK", "DE", "IN", "AU", "SG"]

FAILURE_SYMPTOMS = {
    "MB": ["Won't power on", "Random shutdowns", "No display output", "Overheating / thermal shutdown"],
    "FAN": ["Loud grinding noise", "Fan not spinning", "Overheating"],
    "BAT": ["Won't hold charge", "Swelling detected", "Battery not detected"],
    "KB": ["Keys unresponsive", "Sticky keys", "Backlight failure"],
    "SSD": ["Boot failure", "Data corruption", "Drive not detected"],
    "RAM": ["Blue screen / crashes", "Memory not detected"],
    "DSP": ["Dead pixels", "Screen flicker", "Backlight bleed"],
    "CAM": ["Camera not detected", "Blurry/no image"],
}


def make_sku(model: str, comp_code: str, idx: int) -> str:
    model_code = "".join(w[0] for w in model.split())[:4].upper()
    return f"{model_code}-{comp_code}-{idx:04d}"


# ---------------------------------------------------------------------
# 1. Internal BOM dataset (structured, "clean")
# ---------------------------------------------------------------------

def generate_internal_bom(n_rows: int = 300):
    rows = []
    skus = []
    for i in range(1, n_rows + 1):
        model = random.choice(LAPTOP_MODELS)
        comp_name, comp_code = random.choice(COMPONENTS)
        sku = make_sku(model, comp_code, i)
        skus.append((sku, model, comp_name, comp_code))

        rows.append({
            "sku": sku,
            "laptop_model": model,
            "component_name": comp_name,
            "component_code": comp_code,
            "manufacturer": random.choice(MANUFACTURERS),
            "unit_cost_usd": round(random.uniform(8, 220), 2),
            "units_shipped": random.randint(500, 20000),
            "warranty_period_months": random.choice([12, 24, 36]),
            "release_date": (datetime(2022, 1, 1) + timedelta(days=random.randint(0, 900))).strftime("%Y-%m-%d"),
        })
    return rows, skus


# ---------------------------------------------------------------------
# 2. Internal warranty claims dataset (structured, event-level)
# ---------------------------------------------------------------------

def generate_warranty_claims(skus, n_rows: int = 800):
    base_failure = {
        "MB": 0.14, "FAN": 0.11, "BAT": 0.09, "KB": 0.06,
        "SSD": 0.04, "RAM": 0.03, "DSP": 0.02, "CAM": 0.02,
    }

    weights = [base_failure[comp_code] for _, _, _, comp_code in skus]

    rows = []
    for i in range(1, n_rows + 1):
        sku, model, comp_name, comp_code = random.choices(skus, weights=weights, k=1)[0]
        claim_date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 900))
        rows.append({
            "claim_id": f"WC-{i:05d}",
            "sku": sku,
            "laptop_model": model,
            "component_name": comp_name,
            "claim_date": claim_date.strftime("%Y-%m-%d"),
            "failure_symptom": random.choice(FAILURE_SYMPTOMS[comp_code]),
            "days_in_service_at_failure": random.randint(10, 1000),
            "repair_cost_usd": round(random.uniform(15, 300), 2),
            "resolution": random.choice(["Replaced", "Repaired", "Refunded", "Pending"]),
        })
    return rows


# ---------------------------------------------------------------------
# 3. Scraped secondary-market listings (messy, "raw web data")
# ---------------------------------------------------------------------

def messy_title(model: str, condition: str) -> str:
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
            "title": messy_title(model, condition),
            "price_raw": f"${price:,.2f}",
            "condition": condition,
            "condition_notes": random.choice(CONDITION_NOTES),
            "seller_rating_pct": round(random.uniform(85.0, 100.0), 1) if random.random() > 0.05 else None,
            "seller_location": random.choice(SELLER_LOCATIONS),
            "shipping_cost_usd": round(random.choice([0, 0, 0, 4.99, 9.99, 14.99]), 2),
            "bids": random.randint(0, 25) if random.random() > 0.4 else None,
            "listed_date": (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 550))).strftime("%Y-%m-%dT%H:%M:%S"),
            "watchers": random.randint(0, 60),
        }

        if random.random() < 0.08:
            listing.pop("price_raw")

        listings.append(listing)
    return listings


# ---------------------------------------------------------------------
# 4. Dirty SKU mapping / crosswalk table (for fuzzy-matching practice)
# ---------------------------------------------------------------------

def dirty_model_name(model: str) -> str:
    """Introduce typos/abbreviations/casing issues, like a real crosswalk export."""
    mutators = [
        lambda m: m.upper(),
        lambda m: m.lower(),
        lambda m: m.replace(" ", ""),
        lambda m: m.replace("Pro", "Pro."),
        lambda m: m.replace("Air", "Ar"),  # typo
        lambda m: m.replace("EliteBook", "Elite Book"),
        lambda m: m + " (Legacy)",
        lambda m: m.split()[0],  # truncated
        lambda m: m,  # unchanged, exact match
    ]
    return random.choice(mutators)(model)


def generate_sku_mapping(skus, n_rows: int = 200):
    rows = []
    sampled = random.sample(skus, min(n_rows, len(skus)))
    for sku, model, comp_name, comp_code in sampled:
        rows.append({
            "external_ref_id": f"EXT-{uuid.uuid4().hex[:8]}",
            "sku": sku,
            "model_name_variant": dirty_model_name(model),
            "component_alias": random.choice([
                comp_name, comp_name.upper(), comp_name.replace(" ", "_"), comp_code
            ]),
            "source_system": random.choice(["Legacy ERP", "PLM Export", "Vendor Portal", "Manual Entry"]),
            "confidence_flag": random.choice(["verified", "unverified", "needs_review"]),
        })
    return rows


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

if __name__ == "__main__":
    import pandas as pd

    bom_rows, skus = generate_internal_bom(300)
    warranty_rows = generate_warranty_claims(skus, 800)
    listings_rows = generate_scraped_listings(500)
    sku_map_rows = generate_sku_mapping(skus, 200)

    pd.DataFrame(bom_rows).to_csv("internal_bom.csv", index=False)
    pd.DataFrame(warranty_rows).to_csv("internal_warranty_claims.csv", index=False)
    pd.DataFrame(sku_map_rows).to_csv("sku_mapping_lookup.csv", index=False)

    with open("scraped_ebay_listings.json", "w") as f:
        for item in listings_rows:
            f.write(json.dumps(item) + "\n")

    print(f"Generated {len(bom_rows)} BOM rows -> internal_bom.csv")
    print(f"Generated {len(warranty_rows)} warranty claim rows -> internal_warranty_claims.csv")
    print(f"Generated {len(listings_rows)} scraped listings -> scraped_ebay_listings.json")
    print(f"Generated {len(sku_map_rows)} SKU mapping rows -> sku_mapping_lookup.csv")
