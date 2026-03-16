# JE Automation Dashboard Demo

This is a small proof-of-concept for your GeoComply case study.

## Run locally

1. Open the folder in VS Code
2. Create a virtual environment if you want
3. Install packages:

```bash
pip install -r requirements.txt
```

4. Run the dashboard:

```bash
streamlit run app.py
```

5. Or run the backend script:

```bash
python pipeline.py
```

## Demo flow

- Upload `journal_entries.xlsx`
- Show the Validation tab
- Show the Mapping Preview tab
- Show the NetSuite Payload tab

This demonstrates:
- debit / credit balancing
- mapping logic
- date normalization
- NetSuite-ready transformation