/* ---- Compare page logic ---- */
(function () {
  const text1Input      = document.getElementById('text1');
  const text2Input      = document.getElementById('text2');
  const compareBtn      = document.getElementById('compareBtn');
  const clearBtn        = document.getElementById('clearCompare');
  const resultsDiv      = document.getElementById('compareResults');
  const diffOutput      = document.getElementById('diffOutput');
  const compareDisc     = document.getElementById('compareDisclaimer');
  const allergenDelta   = document.getElementById('allergenDelta');
  const newAllergenDiv  = document.getElementById('newAllergens');
  const removedAllDiv   = document.getElementById('removedAllergens');
  const unchangedAllDiv = document.getElementById('unchangedAllergens');
  const newAllergenList    = document.getElementById('newAllergenList');
  const removedAllergenList= document.getElementById('removedAllergenList');
  const unchangedAllergenList = document.getElementById('unchangedAllergenList');

  compareBtn.addEventListener('click', () => {
    const t1 = text1Input.value.trim();
    const t2 = text2Input.value.trim();

    if (!t1 || !t2) {
      showError('Please provide both ingredient lists.');
      return;
    }

    compareBtn.disabled = true;
    compareBtn.textContent = 'Comparing…';

    fetch('/api/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text1: t1, text2: t2, allergens: PROFILE_ALLERGENS })
    })
    .then(r => r.json())
    .then(data => {
      compareBtn.disabled = false;
      compareBtn.textContent = '🔄 Compare Labels';
      if (data.error) { showError(data.error); return; }
      displayCompare(data);
    })
    .catch(() => {
      compareBtn.disabled = false;
      compareBtn.textContent = '🔄 Compare Labels';
      showError('Request failed. Please try again.');
    });
  });

  function displayCompare(data) {
    resultsDiv.classList.remove('hidden');
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Diff
    diffOutput.innerHTML = '';
    (data.diff || []).forEach(chunk => {
      const span = document.createElement('span');
      if (chunk.type === 'added') {
        span.className = 'diff-added';
        span.textContent = ' ' + chunk.text + ' ';
      } else if (chunk.type === 'removed') {
        span.className = 'diff-removed';
        span.textContent = ' ' + chunk.text + ' ';
      } else {
        span.textContent = ' ' + chunk.text + ' ';
      }
      diffOutput.appendChild(span);
    });

    // Allergen delta
    const hasNew     = Object.keys(data.new_allergens || {}).length > 0;
    const hasRemoved = Object.keys(data.removed_allergens || {}).length > 0;
    const unchanged  = {};
    for (const k of Object.keys(data.updated_allergens || {})) {
      if (!data.new_allergens[k]) unchanged[k] = data.updated_allergens[k];
    }
    const hasUnchanged = Object.keys(unchanged).length > 0;

    allergenDelta.classList.remove('hidden');

    if (hasNew) {
      newAllergenDiv.classList.remove('hidden');
      newAllergenList.innerHTML = renderAllergenList(data.new_allergens);
    } else { newAllergenDiv.classList.add('hidden'); }

    if (hasRemoved) {
      removedAllDiv.classList.remove('hidden');
      removedAllergenList.innerHTML = renderAllergenList(data.removed_allergens);
    } else { removedAllDiv.classList.add('hidden'); }

    if (hasUnchanged) {
      unchangedAllDiv.classList.remove('hidden');
      unchangedAllergenList.innerHTML = renderAllergenList(unchanged);
    } else { unchangedAllDiv.classList.add('hidden'); }

    compareDisc.textContent = data.disclaimer || '';
  }

  function renderAllergenList(obj) {
    return Object.entries(obj).map(([allergen, terms]) => `
      <div class="allergen-result-item">
        <div class="allergen-result-name">${capitalize(allergen)}</div>
        <div class="allergen-result-terms">
          ${terms.map(t => `<span class="term-chip">${t}</span>`).join('')}
        </div>
      </div>`).join('');
  }

  clearBtn.addEventListener('click', () => {
    text1Input.value = '';
    text2Input.value = '';
    resultsDiv.classList.add('hidden');
    document.getElementById('compareError')?.remove();
  });

  function showError(msg) {
    document.getElementById('compareError')?.remove();
    const div = document.createElement('div');
    div.id = 'compareError';
    div.className = 'alert alert-warning mt-4';
    div.style.marginTop = '.75rem';
    div.innerHTML = `<span>${msg}</span><button class="alert-close" onclick="this.parentElement.remove()">×</button>`;
    compareBtn.parentElement.insertAdjacentElement('afterend', div);
  }

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
})();
