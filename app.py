
import io
import json
from pathlib import Path
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
MAPPING_PATH = BASE_DIR / "mapping.json"
SAMPLE_PATH = BASE_DIR / "journal_entries.xlsx"

st.set_page_config(page_title="JE Automation Demo", page_icon="📊", layout="wide")

@st.cache_data
def load_mapping():
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_date(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    return parsed.dt.strftime("%d/%m/%Y")

def extract_account_code(account_value):
    if pd.isna(account_value):
        return None
    return str(account_value).split(" ")[0].strip()

def validate_rows(df: pd.DataFrame) -> list[str]:
    errors = []
    required_cols = ["Subsidiary", "Date", "Account", "Debit", "Credit", "Location", "Currency"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        return errors

    debit = pd.to_numeric(df["Debit"], errors="coerce").fillna(0)
    credit = pd.to_numeric(df["Credit"], errors="coerce").fillna(0)

    both_filled = ((debit > 0) & (credit > 0)).sum()
    both_empty = ((debit == 0) & (credit == 0)).sum()

    if both_filled:
        errors.append(f"{both_filled} row(s) have both Debit and Credit filled.")
    if both_empty:
        errors.append(f"{both_empty} row(s) have neither Debit nor Credit filled.")

    total_debit = debit.sum()
    total_credit = credit.sum()
    if round(total_debit, 2) != round(total_credit, 2):
        errors.append(
            f"Batch is unbalanced. Total Debit = {total_debit:,.2f}, Total Credit = {total_credit:,.2f}"
        )

    normalized = pd.to_datetime(df["Date"], errors="coerce")
    bad_dates = normalized.isna().sum()
    if bad_dates:
        errors.append(f"{bad_dates} row(s) have invalid dates.")

    return errors

def apply_mapping(df: pd.DataFrame, mapping: dict):
    out = df.copy()

    out["Debit"] = pd.to_numeric(out["Debit"], errors="coerce")
    out["Credit"] = pd.to_numeric(out["Credit"], errors="coerce")
    out["Subsidiary_ID"] = out["Subsidiary"].map(mapping["subsidiary"])
    out["Currency_Code"] = out["Currency"].map(mapping["currency"])
    out["Location_Code"] = out["Location"].map(mapping["location"])
    out["Account_Code"] = out["Account"].apply(extract_account_code)
    out["Normalized_Date"] = normalize_date(out["Date"])

    unmapped = {}
    for col, mapped_col in [
        ("Subsidiary", "Subsidiary_ID"),
        ("Currency", "Currency_Code"),
        ("Location", "Location_Code"),
    ]:
        bad = out[out[mapped_col].isna()][col].dropna().astype(str).unique().tolist()
        if bad:
            unmapped[col] = bad

    payload_cols = [
        "Subsidiary_ID",
        "Normalized_Date",
        "Account_Code",
        "Debit",
        "Credit",
        "Location_Code",
        "Currency_Code",
    ]
    payload = out[payload_cols].rename(
        columns={"Normalized_Date": "Date"}
    ).to_dict(orient="records")

    return out, payload, unmapped

def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Results") -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    buffer.seek(0)
    return buffer.getvalue()

st.title("📊 Journal Entry Automation Demo")
st.caption("Proof-of-concept dashboard for GeoComply case study: Excel → Validation → Mapping → NetSuite-ready payload")

mapping = load_mapping()

with st.sidebar:
    st.header("Demo Files")
    st.write("Use the sample file or upload your own Excel file.")
    with open(SAMPLE_PATH, "rb") as f:
        st.download_button(
            "Download sample Excel",
            data=f.read(),
            file_name="journal_entries.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with open(MAPPING_PATH, "rb") as f:
        st.download_button(
            "Download mapping.json",
            data=f.read(),
            file_name="mapping.json",
            mime="application/json",
            use_container_width=True,
        )

uploaded = st.file_uploader("Upload a journal entry Excel file (.xlsx)", type=["xlsx"])

if uploaded is None:
    st.info("Upload the sample Excel file from the sidebar to test the prototype.")
    st.stop()

try:
    df = pd.read_excel(uploaded)
except Exception as e:
    st.error(f"Could not read the Excel file: {e}")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["Input Data", "Validation", "Mapping Preview", "NetSuite Payload"])

with tab1:
    st.subheader("Uploaded Journal Entries")
    st.dataframe(df, use_container_width=True)

errors = validate_rows(df)
mapped_df, payload, unmapped = apply_mapping(df, mapping)

with tab2:
    st.subheader("Validation Results")

    total_debit = pd.to_numeric(df["Debit"], errors="coerce").fillna(0).sum() if "Debit" in df.columns else 0
    total_credit = pd.to_numeric(df["Credit"], errors="coerce").fillna(0).sum() if "Credit" in df.columns else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Debit", f"{total_debit:,.2f}")
    c2.metric("Total Credit", f"{total_credit:,.2f}")
    c3.metric("Status", "PASS" if not errors else "FAIL")

    if errors:
        for err in errors:
            st.error(err)
    else:
        st.success("All validation checks passed.")

with tab3:
    st.subheader("Mapped Output")
    st.dataframe(mapped_df, use_container_width=True)
    if unmapped:
        st.warning("Some values could not be mapped:")
        st.json(unmapped)
    else:
        st.success("All mapped fields resolved successfully.")

with tab4:
    st.subheader("NetSuite-ready Payload")
    st.json(payload)

st.divider()
left, right = st.columns(2)

with left:
    st.download_button(
        "Download mapped results (.xlsx)",
        data=to_excel_bytes(mapped_df, sheet_name="Mapped Results"),
        file_name="mapped_journal_entries.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

with right:
    st.download_button(
        "Download payload (.json)",
        data=json.dumps(payload, indent=2),
        file_name="netsuite_payload.json",
        mime="application/json",
        use_container_width=True,
    )

st.markdown("### How to demo this")
st.markdown(
    """
1. Upload the Excel file.  
2. Show the validation tab proving debit/credit balancing.  
3. Show the mapping preview with transformed subsidiary, location, and currency values.  
4. Open the payload tab and explain this would be the object sent to NetSuite after approval.
"""
)
