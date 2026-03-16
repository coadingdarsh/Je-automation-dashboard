
import json
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
MAPPING_PATH = BASE_DIR / "mapping.json"
INPUT_PATH = BASE_DIR / "journal_entries.xlsx"

def normalize_date(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    return parsed.dt.strftime("%d/%m/%Y")

def extract_account_code(account_value):
    if pd.isna(account_value):
        return None
    return str(account_value).split(" ")[0].strip()

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    df = pd.read_excel(INPUT_PATH)

    debit = pd.to_numeric(df["Debit"], errors="coerce").fillna(0)
    credit = pd.to_numeric(df["Credit"], errors="coerce").fillna(0)

    if round(debit.sum(), 2) != round(credit.sum(), 2):
        raise ValueError(
            f"Validation failed: Debit ({debit.sum():,.2f}) does not equal Credit ({credit.sum():,.2f})"
        )

    out = df.copy()
    out["Subsidiary_ID"] = out["Subsidiary"].map(mapping["subsidiary"])
    out["Currency_Code"] = out["Currency"].map(mapping["currency"])
    out["Location_Code"] = out["Location"].map(mapping["location"])
    out["Account_Code"] = out["Account"].apply(extract_account_code)
    out["Normalized_Date"] = normalize_date(out["Date"])

    payload_cols = [
        "Subsidiary_ID",
        "Normalized_Date",
        "Account_Code",
        "Debit",
        "Credit",
        "Location_Code",
        "Currency_Code",
    ]
    payload = out[payload_cols].rename(columns={"Normalized_Date": "Date"}).to_dict(orient="records")

    mapped_path = OUTPUT_DIR / "mapped_journal_entries.xlsx"
    payload_path = OUTPUT_DIR / "netsuite_payload.json"

    with pd.ExcelWriter(mapped_path, engine="openpyxl") as writer:
        out.to_excel(writer, index=False, sheet_name="Mapped Results")

    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("Validation passed.")
    print(f"Mapped Excel saved to: {mapped_path}")
    print(f"JSON payload saved to: {payload_path}")

if __name__ == "__main__":
    main()
