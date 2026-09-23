# AI Post Office Identifier

<p align="center">
  <img src="https://img.shields.io/badge/AI-Postal%20Address%20Matcher-blueviolet" alt="AI Postal Address Matcher" />
  <img src="https://img.shields.io/badge/Python-FastAPI-3776AB" alt="Python FastAPI" />
  <img src="https://img.shields.io/badge/Frontend-React-61DAFB" alt="Frontend React" />
  <img src="https://img.shields.io/badge/Goal-Post%20Office%20%26%20PIN%20Detection-success" alt="Post Office Detection" />
</p>

> Smart postal address understanding for India — identify the correct Post Office and PIN code from messy or incomplete address data.

This project was fully developed by the author as a practical AI-driven solution for Indian postal address normalization and Post Office identification.

## Overview

The system takes raw address text, understands key postal fields such as locality, district, state, landmark, and PIN code, and matches them against a local postal database to identify the most likely Post Office. It uses AI/NLP parsing when available and falls back to a rule-based parser when needed.

This solution is designed to handle real Indian address variations such as:

- short or informal locality names
- missing district or state details
- spelling variations
- landmark-based references
- wrong or mismatched PIN codes

## Why this project matters

Indian addresses are often written in unstructured or inconsistent formats. In many cases, a person provides only part of the address, a nearby landmark, or a shortened locality name. Manually identifying the correct Post Office and PIN code can be slow and error-prone.

This application solves that problem by normalizing address inputs and matching them against a postal dataset to suggest the best candidate office with confidence-based reasoning.

## Features

- Raw address input and validation
- AI-based address parsing with LLM support
- Rule-based fallback parser when AI is unavailable
- Fuzzy matching against postal records
- Confidence scoring for the best result
- Alternative office suggestions
- PIN mismatch detection and warnings
- User prompts for missing information when confidence is low
- Image upload and camera capture support for address scanning
- Clean React frontend for result visualization

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
- RapidFuzz
- SQLite / local postal dataset

### AI and Parsing
- OpenAI-compatible API support
- Rule-based fallback parser

## Architecture

The application is built with a simple two-part architecture:

1. Frontend interface
   - accepts address input or image upload
   - displays parsed output and best matches
   - shows confidence and alternatives

2. Backend API
   - parses and normalizes the address
   - searches postal data using locality, district, state, and PIN
   - returns the best Post Office match with explanations

## Project Structure

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
│   │   ├── postal.db
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── src/
│   │   ├── index.html
│   │   ├── package.json
│   │   └── vite.config.js
│   └── README.md
├── run_full_app.ps1
└── README.md
```

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

API docs will be available at:

- http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will run at:

- http://localhost:5173

### 3. Run both together

```powershell
./run_full_app.ps1
```

## Example Inputs

- near KGiSL college, Saravanampatti, Coimbatore, Tamil Nadu
- Anna Nagar, Chennai, Tamil Nadu
- RS Puram CBE TamilNadu 641002
- Saravanampatti, Coimbatore, 641035

## Important Note

This project uses a prototype local postal dataset for demonstration and research purposes. It is not directly integrated with official India Post live systems.

## Future Improvements

- official postal data integration
- multilingual address parsing
- improved OCR and handwriting support
- better confidence modeling
- production-ready deployment

## Conclusion

This project demonstrates a practical and intelligent way to solve Indian postal address ambiguity using AI, fuzzy matching, and structured postal data. It provides a smart and user-friendly way to identify the correct Post Office and PIN code from imperfect address inputs.

This repository represents a complete solution developed by the author for postal intelligence and address normalization.


<<<<<<< HEAD
The frontend typically runs at:

- http://localhost:5173

---

## Run All in One Command

A PowerShell wrapper is included to run the project together:
=======
Frontend will run at:

- http://localhost:5173

### 3. Run both together
>>>>>>> e473fe3 (Improve GitHub presentation)

```powershell
./run_full_app.ps1
```

<<<<<<< HEAD
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
=======
## Example Inputs

- near KGiSL college, Saravanampatti, Coimbatore, Tamil Nadu
- Anna Nagar, Chennai, Tamil Nadu
- RS Puram CBE TamilNadu 641002
- Saravanampatti, Coimbatore, 641035

## Important Note

This project uses a prototype local postal dataset for demonstration and research purposes. It is not directly integrated with official India Post live systems.

## Future Improvements

- official postal data integration
- multilingual address parsing
- improved OCR and handwriting support
- better confidence modeling
- production-ready deployment

## Conclusion

This project demonstrates a practical and intelligent way to solve Indian postal address ambiguity using AI, fuzzy matching, and structured postal data. It provides a smart and user-friendly way to identify the correct Post Office and PIN code from imperfect address inputs.

This repository represents a complete solution developed by the author for postal intelligence and address normalization.
>>>>>>> e473fe3 (Improve GitHub presentation)
