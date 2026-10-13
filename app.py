import os
import sqlite3
import uuid
import json
import re
import difflib
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session, flash
)
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')

TESSERACT_CMD = os.environ.get('TESSERACT_CMD', '/usr/bin/tesseract')
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(__file__), 'data', 'allergylens.db'))
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), 'uploads'))
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
Path(os.path.dirname(DATABASE_PATH)).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Allergen dictionary
# ---------------------------------------------------------------------------

ALLERGEN_DICT = {
    "milk": [
        "milk", "dairy", "lactose", "lactulose", "casein", "caseinate",
        "sodium caseinate", "calcium caseinate", "whey", "whey protein",
        "lactalbumin", "lactoglobulin", "lactoferrin", "butter", "buttermilk",
        "cream", "cheese", "yogurt", "yoghurt", "ghee", "kefir", "curds",
        "half-and-half", "milk solids", "milk powder", "skimmed milk",
        "condensed milk", "evaporated milk", "nougat", "custard", "pudding",
        "rennet", "recaldent", "hydrolysed whey", "milk fat", "milk protein",
        "lactalbumin phosphate", "casein hydrolysate"
    ],
    "peanuts": [
        "peanut", "peanuts", "groundnut", "groundnuts", "monkey nuts",
        "arachis oil", "arachis hypogaea", "beer nuts", "mixed nuts",
        "peanut butter", "peanut flour", "peanut protein", "mandelonas",
        "nu-nuts", "artificial nuts"
    ],
    "tree nuts": [
        "almond", "almonds", "cashew", "cashews", "walnut", "walnuts",
        "pecan", "pecans", "pistachio", "pistachios", "brazil nut", "brazil nuts",
        "hazelnut", "hazelnuts", "macadamia", "macadamia nut", "pine nut", "pine nuts",
        "chestnut", "chestnuts", "coconut", "coconuts", "hickory nut",
        "praline", "marzipan", "gianduja", "nougat", "nut paste", "nut butter",
        "tree nut", "tree nuts", "mixed nuts", "filbert", "filberts",
        "beechnut", "ginkgo nut", "lychee nut", "pili nut", "shea nut"
    ],
    "eggs": [
        "egg", "eggs", "egg white", "egg yolk", "egg powder", "dried egg",
        "whole egg", "egg protein", "albumin", "globulin", "lysozyme",
        "mayonnaise", "meringue", "ovalbumin", "ovomucin", "ovomucoid",
        "ovovitellin", "silici albuminate", "livetin", "lecithin",
        "egg lecithin", "egg substitutes"
    ],
    "soy": [
        "soy", "soya", "soybean", "soybeans", "soy protein", "soya protein",
        "soy flour", "soy milk", "soya milk", "tofu", "miso", "tempeh",
        "edamame", "tamari", "shoyu", "natto", "kinako", "soy sauce",
        "soy lecithin", "hydrolysed soy protein", "textured soy protein",
        "textured vegetable protein", "tvp", "soy isolate", "soy concentrate"
    ],
    "wheat": [
        "wheat", "wheat flour", "whole wheat", "whole grain wheat", "wheat bran",
        "wheat germ", "wheat starch", "wheat protein", "vital wheat gluten",
        "gluten", "semolina", "spelt", "kamut", "einkorn", "emmer", "farro",
        "farina", "durum", "triticale", "bulgur", "freekeh", "couscous",
        "bread flour", "all-purpose flour", "breadcrumbs", "croutons",
        "hydrolysed wheat protein", "wheat grass"
    ],
    "fish": [
        "fish", "anchovy", "anchovies", "bass", "catfish", "cod", "flounder",
        "grouper", "haddock", "hake", "halibut", "herring", "mahi mahi",
        "perch", "pike", "pollock", "salmon", "scrod", "snapper", "sole",
        "swordfish", "tilapia", "trout", "tuna", "whitefish", "walleye",
        "fish sauce", "fish stock", "fish oil", "worcestershire sauce",
        "caesar dressing", "fish gelatin", "surimi"
    ],
    "shellfish": [
        "shellfish", "shrimp", "prawn", "prawns", "lobster", "crab", "crabmeat",
        "crayfish", "crawfish", "langoustine", "scallop", "scallops",
        "clam", "clams", "oyster", "oysters", "mussel", "mussels",
        "abalone", "barnacle", "squid", "octopus", "snail", "escargot",
        "barnacles", "sea urchin", "roe", "imitation crab"
    ],
    "sesame": [
        "sesame", "sesame seed", "sesame seeds", "sesame oil", "sesame flour",
        "tahini", "til", "teel", "gingelly", "gingelly oil", "benne",
        "sesame paste", "sesame butter", "sesame protein", "sesame meal"
    ]
}

# Flatten for quick lookup: term -> allergen category
TERM_TO_ALLERGEN = {}
for allergen, terms in ALLERGEN_DICT.items():
    for term in terms:
        TERM_TO_ALLERGEN[term.lower()] = allergen

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            scan_type TEXT NOT NULL,
            ingredients_text TEXT NOT NULL,
            allergens_found TEXT NOT NULL,
            profile_used TEXT NOT NULL,
            ocr_confidence TEXT,
            notes TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS allergy_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT 'My Profile',
            allergens TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    # Seed a default profile if none exists
    row = conn.execute('SELECT COUNT(*) FROM allergy_profiles').fetchone()
    if row[0] == 0:
        now = datetime.utcnow().isoformat()
        conn.execute(
            'INSERT INTO allergy_profiles (name, allergens, created_at, updated_at) VALUES (?,?,?,?)',
            ('My Profile', json.dumps([]), now, now)
        )
    conn.commit()
    conn.close()


init_db()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def clean_ingredients_text(text):
    """Normalize OCR'd or pasted ingredient text."""
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def detect_allergens(text, selected_allergens):
    """
    Scan ingredient text for allergens.
    Returns dict: {allergen: [matched_terms]}
    """
    text_lower = text.lower()
    found = {}
    uncertain = []

    # Check OCR quality heuristic
    non_alpha = sum(1 for c in text if not c.isalpha() and not c.isspace())
    total = max(len(text), 1)
    ocr_noise_ratio = non_alpha / total

    for allergen in selected_allergens:
        terms = ALLERGEN_DICT.get(allergen, [])
        matches = []
        for term in terms:
            # Use word-boundary aware search
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            if re.search(pattern, text_lower):
                matches.append(term)
        if matches:
            found[allergen] = matches

    return found, ocr_noise_ratio


def ocr_image(filepath):
    """Run Tesseract OCR and return (text, confidence_level)."""
    try:
        img = Image.open(filepath)
        # Get detailed data including confidence
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        # Calculate average confidence (ignore -1 values)
        confidences = [int(c) for c in data['conf'] if int(c) != -1]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        
        text = pytesseract.image_to_string(img, config='--psm 6')
        
        if avg_conf < 30:
            confidence_level = 'low'
        elif avg_conf < 60:
            confidence_level = 'medium'
        else:
            confidence_level = 'high'
        
        return text, confidence_level, avg_conf
    except Exception as e:
        return '', 'failed', 0


def compute_diff(text1, text2):
    """Return word-level diff between two ingredient texts."""
    words1 = text1.lower().split()
    words2 = text2.lower().split()
    
    differ = difflib.SequenceMatcher(None, words1, words2)
    
    result = []
    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        if tag == 'equal':
            result.append({'type': 'equal', 'text': ' '.join(words1[i1:i2])})
        elif tag == 'replace':
            result.append({'type': 'removed', 'text': ' '.join(words1[i1:i2])})
            result.append({'type': 'added', 'text': ' '.join(words2[j1:j2])})
        elif tag == 'delete':
            result.append({'type': 'removed', 'text': ' '.join(words1[i1:i2])})
        elif tag == 'insert':
            result.append({'type': 'added', 'text': ' '.join(words2[j1:j2])})
    
    return result


def get_active_profile():
    conn = get_db()
    row = conn.execute('SELECT * FROM allergy_profiles ORDER BY updated_at DESC LIMIT 1').fetchone()
    conn.close()
    if row:
        return dict(row)
    return {'id': None, 'name': 'My Profile', 'allergens': '[]'}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    profile = get_active_profile()
    profile['allergens'] = json.loads(profile['allergens'])
    return render_template('index.html', profile=profile)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    conn = get_db()
    if request.method == 'POST':
        name = request.form.get('name', 'My Profile').strip() or 'My Profile'
        selected = request.form.getlist('allergens')
        now = datetime.utcnow().isoformat()
        row = conn.execute('SELECT id FROM allergy_profiles ORDER BY updated_at DESC LIMIT 1').fetchone()
        if row:
            conn.execute(
                'UPDATE allergy_profiles SET name=?, allergens=?, updated_at=? WHERE id=?',
                (name, json.dumps(selected), now, row['id'])
            )
        else:
            conn.execute(
                'INSERT INTO allergy_profiles (name, allergens, created_at, updated_at) VALUES (?,?,?,?)',
                (name, json.dumps(selected), now, now)
            )
        conn.commit()
        conn.close()
        flash('Profile saved successfully.', 'success')
        return redirect(url_for('profile'))
    
    row = conn.execute('SELECT * FROM allergy_profiles ORDER BY updated_at DESC LIMIT 1').fetchone()
    conn.close()
    current = dict(row) if row else {'name': 'My Profile', 'allergens': '[]'}
    current['allergens'] = json.loads(current['allergens'])
    all_allergens = list(ALLERGEN_DICT.keys())
    return render_template('profile.html', profile=current, all_allergens=all_allergens)


@app.route('/scan', methods=['GET'])
def scan():
    profile = get_active_profile()
    profile['allergens'] = json.loads(profile['allergens'])
    return render_template('scan.html', profile=profile)


@app.route('/api/ocr', methods=['POST'])
def api_ocr():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only JPG and PNG files are allowed'}), 400
    
    filename = str(uuid.uuid4()) + '.' + secure_filename(file.filename).rsplit('.', 1)[-1].lower()
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        text, confidence_level, avg_conf = ocr_image(filepath)
        cleaned = clean_ingredients_text(text)
        return jsonify({
            'text': cleaned,
            'confidence': confidence_level,
            'confidence_score': round(avg_conf, 1),
            'warning': confidence_level in ('low', 'failed')
        })
    except Exception as e:
        return jsonify({'error': 'OCR processing failed. Please try manual entry.'}), 500
    finally:
        # Clean up uploaded file
        try:
            os.remove(filepath)
        except Exception:
            pass


@app.route('/api/check', methods=['POST'])
def api_check():
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    selected_allergens = data.get('allergens', [])
    save_to_history = data.get('save', True)
    scan_type = data.get('scan_type', 'manual')
    ocr_confidence = data.get('ocr_confidence', None)

    if not text:
        return jsonify({'error': 'No ingredient text provided'}), 400

    if not selected_allergens:
        return jsonify({'error': 'No allergens selected in your profile'}), 400

    cleaned = clean_ingredients_text(text)
    found, noise_ratio = detect_allergens(cleaned, selected_allergens)

    # Build warning if text looks garbled
    quality_warning = None
    if noise_ratio > 0.3:
        quality_warning = 'The ingredient text contains many unusual characters. OCR may have misread the label. Please verify the text manually before relying on these results.'

    result = {
        'found': found,
        'checked_allergens': selected_allergens,
        'text_used': cleaned,
        'quality_warning': quality_warning,
        'disclaimer': (
            'This tool assists with identifying potential allergens but cannot guarantee food safety. '
            'It does not detect cross-contact or manufacturing contamination. Always read physical labels '
            'and consult a healthcare professional if you have severe allergies.'
        )
    }

    if save_to_history:
        try:
            conn = get_db()
            now = datetime.utcnow().isoformat()
            profile = get_active_profile()
            conn.execute(
                '''INSERT INTO scans (created_at, scan_type, ingredients_text, allergens_found, profile_used, ocr_confidence, notes)
                   VALUES (?,?,?,?,?,?,?)''',
                (now, scan_type, cleaned, json.dumps(found),
                 profile.get('name', 'Unknown'), ocr_confidence, quality_warning)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # Don't fail the response if history save fails

    return jsonify(result)


@app.route('/api/compare', methods=['POST'])
def api_compare():
    data = request.get_json(silent=True) or {}
    text1 = data.get('text1', '').strip()
    text2 = data.get('text2', '').strip()
    selected_allergens = data.get('allergens', [])

    if not text1 or not text2:
        return jsonify({'error': 'Both ingredient texts are required'}), 400

    diff = compute_diff(text1, text2)

    # Run allergen checks on both
    found1, _ = detect_allergens(text1, selected_allergens)
    found2, _ = detect_allergens(text2, selected_allergens)

    # New allergens in text2 that weren't in text1
    new_allergens = {k: v for k, v in found2.items() if k not in found1}
    removed_allergens = {k: v for k, v in found1.items() if k not in found2}

    return jsonify({
        'diff': diff,
        'original_allergens': found1,
        'updated_allergens': found2,
        'new_allergens': new_allergens,
        'removed_allergens': removed_allergens,
        'disclaimer': (
            'Comparison results highlight textual differences only. '
            'Always verify with physical labels.'
        )
    })


@app.route('/history')
def history():
    conn = get_db()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    total = conn.execute('SELECT COUNT(*) FROM scans').fetchone()[0]
    rows = conn.execute(
        'SELECT * FROM scans ORDER BY created_at DESC LIMIT ? OFFSET ?',
        (per_page, offset)
    ).fetchall()
    conn.close()

    scans = []
    for row in rows:
        s = dict(row)
        s['allergens_found'] = json.loads(s['allergens_found'])
        scans.append(s)

    total_pages = (total + per_page - 1) // per_page
    return render_template('history.html', scans=scans, page=page,
                           total_pages=total_pages, total=total)


@app.route('/history/delete/<int:scan_id>', methods=['POST'])
def delete_scan(scan_id):
    conn = get_db()
    conn.execute('DELETE FROM scans WHERE id = ?', (scan_id,))
    conn.commit()
    conn.close()
    flash('Scan record deleted.', 'info')
    return redirect(url_for('history'))


@app.route('/history/delete-all', methods=['POST'])
def delete_all_scans():
    conn = get_db()
    conn.execute('DELETE FROM scans')
    conn.commit()
    conn.close()
    flash('All scan history deleted.', 'info')
    return redirect(url_for('history'))


@app.route('/compare')
def compare():
    profile = get_active_profile()
    profile['allergens'] = json.loads(profile['allergens'])
    return render_template('compare.html', profile=profile)


@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 10 MB.'}), 413


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
