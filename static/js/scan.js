/* ---- Scan page logic ---- */
(function () {
  const uploadZone    = document.getElementById('uploadZone');
  const imageInput    = document.getElementById('imageInput');
  const previewCont   = document.getElementById('previewContainer');
  const imagePreview  = document.getElementById('imagePreview');
  const clearImageBtn = document.getElementById('clearImage');
  const ocrStatus     = document.getElementById('ocrStatus');
  const ocrBadge      = document.getElementById('ocrConfidenceBadge');
  const tabBtns       = document.querySelectorAll('.tab-btn');
  const tabUpload     = document.getElementById('tab-upload');
  const tabManual     = document.getElementById('tab-manual');
  const manualText    = document.getElementById('manualText');
  const ingredientText= document.getElementById('ingredientText');
  const checkBtn      = document.getElementById('checkBtn');
  const clearScanBtn  = document.getElementById('clearScan');
  const resultsCard   = document.getElementById('resultsCard');
  const qualityWarn   = document.getElementById('qualityWarning');
  const qualityText   = document.getElementById('qualityWarningText');
  const allergensFound= document.getElementById('allergensFound');
  const noAllergens   = document.getElementById('noAllergensFound');
  const allergenList  = document.getElementById('allergenList');
  const disclaimer    = document.getElementById('resultDisclaimer');
  const saveNote      = document.getElementById('saveNote');

  let currentTab = 'upload';
  let lastOcrConfidence = null;

  // ---- Tabs ----
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTab = btn.dataset.tab;
      if (currentTab === 'upload') {
        tabUpload.classList.remove('hidden');
        tabManual.classList.add('hidden');
      } else {
        tabManual.classList.remove('hidden');
        tabUpload.classList.add('hidden');
      }
    });
  });

  // ---- Upload zone ----
  uploadZone.addEventListener('click', (e) => {
    if (e.target !== imageInput) imageInput.click();
  });
  uploadZone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); imageInput.click(); }
  });
  uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault(); uploadZone.classList.remove('drag-over');
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  });

  imageInput.addEventListener('change', () => {
    if (imageInput.files[0]) handleFile(imageInput.files[0]);
  });

  clearImageBtn.addEventListener('click', () => {
    imageInput.value = '';
    previewCont.classList.add('hidden');
    uploadZone.classList.remove('hidden');
    ingredientText.value = '';
    ocrBadge.className = 'ocr-confidence hidden';
    lastOcrConfidence = null;
  });

  function handleFile(file) {
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      showInlineError('Only JPG and PNG files are supported.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showInlineError('File too large. Maximum size is 10 MB.');
      return;
    }

    // Preview
    const reader = new FileReader();
    reader.onload = (e) => {
      imagePreview.src = e.target.result;
      previewCont.classList.remove('hidden');
      uploadZone.style.display = 'none';
    };
    reader.readAsDataURL(file);

    // OCR
    runOCR(file);
  }

  function runOCR(file) {
    ocrStatus.classList.remove('hidden');
    ingredientText.value = '';
    ocrBadge.className = 'ocr-confidence hidden';

    const formData = new FormData();
    formData.append('image', file);

    fetch('/api/ocr', { method: 'POST', body: formData })
      .then(r => r.json())
      .then(data => {
        ocrStatus.classList.add('hidden');
        if (data.error) {
          showInlineError(data.error);
          return;
        }
        ingredientText.value = data.text || '';
        lastOcrConfidence = data.confidence;
        const confLabels = { high: '✓ OCR confidence: High', medium: '⚠ OCR confidence: Medium — verify text', low: '⚠ OCR confidence: Low — please verify or use manual entry', failed: '✗ OCR failed — please use manual entry' };
        ocrBadge.textContent = confLabels[data.confidence] || '';
        ocrBadge.className = `ocr-confidence conf-${data.confidence}`;
        if (data.warning) {
          showQualityWarning('Low OCR confidence. Please review and correct the extracted text before checking.');
        }
      })
      .catch(() => {
        ocrStatus.classList.add('hidden');
        showInlineError('OCR request failed. Try manual entry.');
      });
  }

  // ---- Manual text sync ----
  manualText.addEventListener('input', () => {
    ingredientText.value = manualText.value;
  });

  // ---- Check button ----
  checkBtn.addEventListener('click', () => {
    const text = ingredientText.value.trim();
    if (!text) {
      showInlineError('Please provide ingredient text first.');
      return;
    }
    if (!PROFILE_ALLERGENS || PROFILE_ALLERGENS.length === 0) {
      showInlineError('Your allergy profile is empty. Please set it up first.');
      return;
    }

    checkBtn.disabled = true;
    checkBtn.textContent = 'Checking…';

    const payload = {
      text,
      allergens: PROFILE_ALLERGENS,
      save: true,
      scan_type: currentTab === 'upload' ? 'ocr' : 'manual',
      ocr_confidence: lastOcrConfidence
    };

    fetch('/api/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
      checkBtn.disabled = false;
      checkBtn.textContent = '🔍 Check Ingredients';
      if (data.error) { showInlineError(data.error); return; }
      displayResults(data);
    })
    .catch(() => {
      checkBtn.disabled = false;
      checkBtn.textContent = '🔍 Check Ingredients';
      showInlineError('Request failed. Please try again.');
    });
  });

  function displayResults(data) {
    resultsCard.classList.remove('hidden');
    resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Quality warning
    if (data.quality_warning) {
      showQualityWarning(data.quality_warning);
    } else {
      qualityWarn.classList.add('hidden');
    }

    const found = data.found || {};
    const hasFound = Object.keys(found).length > 0;

    if (hasFound) {
      allergensFound.classList.remove('hidden');
      noAllergens.classList.add('hidden');
      allergenList.innerHTML = '';
      for (const [allergen, terms] of Object.entries(found)) {
        const item = document.createElement('div');
        item.className = 'allergen-result-item';
        item.innerHTML = `
          <div class="allergen-result-name">⚠ ${capitalize(allergen)}</div>
          <div class="allergen-result-terms">
            ${terms.map(t => `<span class="term-chip">${t}</span>`).join('')}
          </div>`;
        allergenList.appendChild(item);
      }
    } else {
      noAllergens.classList.remove('hidden');
      allergensFound.classList.add('hidden');
    }

    disclaimer.textContent = data.disclaimer || '';
    saveNote.classList.remove('hidden');
  }

  function showQualityWarning(msg) {
    qualityWarn.classList.remove('hidden');
    qualityText.textContent = '⚠ ' + msg;
  }

  function showInlineError(msg) {
    // Show near button
    let existing = document.getElementById('inlineScanError');
    if (existing) existing.remove();
    const div = document.createElement('div');
    div.id = 'inlineScanError';
    div.className = 'alert alert-warning';
    div.style.marginTop = '.75rem';
    div.innerHTML = `<span>${msg}</span><button class="alert-close" onclick="this.parentElement.remove()">×</button>`;
    checkBtn.parentElement.insertAdjacentElement('afterend', div);
  }

  // ---- Clear ----
  clearScanBtn.addEventListener('click', () => {
    imageInput.value = '';
    previewCont.classList.add('hidden');
    uploadZone.style.display = '';
    ingredientText.value = '';
    manualText.value = '';
    ocrBadge.className = 'ocr-confidence hidden';
    resultsCard.classList.add('hidden');
    qualityWarn.classList.add('hidden');
    lastOcrConfidence = null;
    saveNote.classList.add('hidden');
    document.getElementById('inlineScanError')?.remove();
  });

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
})();
