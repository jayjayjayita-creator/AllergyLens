# AllergyLens

A food allergy ingredient checker that uses OCR to scan labels and detect allergens.

## Quick Start (Docker)

```bash
docker compose up --build
```

Open **http://localhost:5000**

SQLite data persists in the `allergylens_data` Docker volume.

## What It Does

- Upload a food label photo (JPG/PNG) → OCR extracts ingredients → allergen check
- Manual text entry when OCR fails
- 9 major allergens: milk, peanuts, tree nuts, eggs, soy, wheat, fish, shellfish, sesame
- Detects hidden names (casein/whey for milk, arachis oil for peanuts, tahini for sesame, etc.)
- Compare two ingredient lists to spot what changed
- Scan history stored in SQLite with delete support

## Local Python Setup (optional)

**Requirements:** Python 3.11+, Tesseract OCR installed on your system.

```bash
# Install Tesseract
# macOS:  brew install tesseract
# Ubuntu: sudo apt install tesseract-ocr
# Windows: https://github.com/UB-Mannheim/tesseract/wiki

pip install -r requirements.txt

export DATABASE_PATH=./data/allergylens.db
export UPLOAD_FOLDER=./uploads
export TESSERACT_CMD=/usr/bin/tesseract   # adjust path for your OS

mkdir -p data uploads
python app.py
```

Open **http://localhost:5000**

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_PATH` | `/app/data/allergylens.db` | SQLite file path |
| `UPLOAD_FOLDER` | `/app/uploads` | Temp upload directory |
| `TESSERACT_CMD` | `/usr/bin/tesseract` | Tesseract binary path |
| `SECRET_KEY` | dev string | Flask session key — change in production |

## Disclaimer

AllergyLens is an informational tool only. It does not guarantee food safety, cannot detect cross-contact contamination, and is not a substitute for medical advice. Always read physical labels.
"# AllergyLens" 
