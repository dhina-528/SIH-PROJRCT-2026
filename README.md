# AI-Powered Indian Post Office Identifier

This project was fully developed by the author as a complete end-to-end solution for identifying the correct Indian Post Office and PIN code from messy or incomplete address data.

## Overview

The system takes raw address text, understands the important postal fields such as locality, district, state, landmark, and PIN code, and matches them against a local postal database to identify the most likely Post Office. It uses AI/NLP parsing when available and falls back to a rule-based parser when needed.

The solution is designed to handle real-world Indian address variations, including:

- short or informal locality names
- missing or incomplete state/district information
- spelling variations
- landmark-based references
- wrong or mismatched PIN codes

---

## Problem Statement

Indian addresses are often written in unstructured or inconsistent formats. People may provide a locality name, nearby landmark, district, or only a shortened version of the address. Manually identifying the correct Post Office and PIN code can be slow and error-prone.

This project solves that by automatically normalizing the address and matching it against a postal dataset to suggest the best possible Post Office and PIN code.

---

## Features

- Raw address input with validation
- AI-based address parsing using OpenAI-compatible LLM support
- Rule-based fallback parser for offline or no-API-key scenarios
- Postal record matching using locality, district, state, office name, and PIN
- Confidence score for each match
- Alternative candidate suggestions when confidence is not high
- PIN mismatch detection and warnings
- User prompts for missing address details when needed
- Camera capture and image upload support for address scanning
- Modern React-based frontend UI

---

## Tech Stack

### Frontend
- React
- Vite
- JavaScript / JSX
- Tesseract.js for OCR support

### Backend
- Python
- FastAPI
- Pydantic
- RapidFuzz for fuzzy matching
- SQLite / postal dataset storage

### AI / Parsing
- OpenAI API support (optional)
- Rule-based parser fallback

---

## Project Architecture

The application has two major parts:

1. Frontend UI
   - Accepts the address input
   - Supports OCR/image upload
   - Displays the parsed result and confidence

2. Backend API
   - Parses the input address
   - Normalizes the address fields
   - Searches the postal dataset
   - Returns the best match and alternatives

---

## Folder Structure

```bash
SIH/
├── aipin/
│   ├── backend/
│   │   ├── data/
│   │   │   └── pincode-data.csv
│   │   ├── scripts/
│   │   │   ├── import_data.py
│   │   │   └── test_scenarios.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── address_parser.py
│   │   │   ├── db.py
│   │   │   └── matcher.py
│   │   ├── tests/
│   │   │   ├── test_locality_filter.py
│   │   │   └── test_parser_aliases.py
│   │   ├── main.py
│   │   └── requirements.txt
│   └── frontend/
│       ├── src/
│       ├── index.html
│       ├── package.json
│       └── vite.config.js
├── run_full_app.ps1
└── README.md
```

---

## How It Works

1. The user enters or uploads an address.
2. The backend parses the address into structured components.
3. The system searches the database for matching postal records.
4. It scores each candidate using fuzzy matching and weighted rules.
5. The best result is returned with confidence and explanation.
6. If the result is uncertain, alternatives are shown and the user can provide more information.

---

## Example Use Cases

- Identify the correct Post Office from a short address string
- Validate whether the provided PIN code matches the expected office
- Help logistics teams improve delivery address verification
- Assist users in understanding postal data for Indian locations

---

## Setup Instructions

### 1. Backend Setup

```bash
cd aipin/backend
pip install -r requirements.txt
```

Run the FastAPI server:

```bash
uvicorn main:app --reload
```

The backend will be available at:

- http://localhost:8000
- Swagger docs: http://localhost:8000/docs

### 2. Frontend Setup

```bash
cd aipin/frontend
npm install
npm run dev
```

The frontend typically runs at:

- http://localhost:5173

---

## Run All in One Command

A PowerShell wrapper is included to run the project together:

```powershell
./run_full_app.ps1
```

---

## Important Note

This project uses a prototype or local postal dataset and is intended for demonstration and research purposes. It is not directly integrated with official India Post live systems.

---

## Future Improvements

- live official postal data integration
- advanced multilingual address parsing
- improved OCR for handwritten or damaged labels
- better confidence model and explainability
- deployment for production use

---

## Conclusion

This project demonstrates an intelligent and practical approach to solving Indian postal address ambiguity using AI and data-driven matching. It provides a smart and user-friendly way to identify the correct Post Office and PIN code from imperfect address inputs.

This repository represents a complete solution developed by the author for the purpose of postal intelligence and address normalization.
