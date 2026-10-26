(() => {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];

  // Subtle pointer depth for primary CTAs; disabled for touch/reduced motion.
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && window.matchMedia('(pointer:fine)').matches) {
    $$('.magnetic').forEach(btn => {
      btn.addEventListener('pointermove', e => {
        const r = btn.getBoundingClientRect();
        btn.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * .06}px, ${(e.clientY - r.top - r.height / 2) * .06}px)`;
      });
      btn.addEventListener('pointerleave', () => { btn.style.transform = ''; });
    });
  }

  // Copy buttons
  $$('.copy-button, .copy-val').forEach(btn => btn.addEventListener('click', async () => {
    const text = (btn.dataset.copy || $('#reference')?.textContent || btn.textContent || '').replace('⧉','').trim();
    if (!text) return;
    const original = btn.innerHTML;
    let copied = false;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        copied = true;
      } else {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        copied = document.execCommand('copy');
        ta.remove();
      }
    } catch (_) { copied = false; }
    btn.innerHTML = copied ? '<span>Copied</span><b>✓</b>' : '<span>Copy failed</span><b>!</b>';
    btn.classList.toggle('copied', copied);
    setTimeout(() => { btn.innerHTML = original; btn.classList.remove('copied'); }, 1800);
  }));

  const form = $('#feedbackForm');
  if (!form) return;

  const desc = $('#description'), count = $('#charCount'), quality = $('#qualityHint');
  const bar = $('#progressBar'), progressText = $('#progressText'), anon = $('#anonymous'), nameField = $('#nameField');
  const file = $('#image'), preview = $('#filePreview'), draftState = $('#draftState');
  const categorySelect = $('#category');

  // AI Assist elements
  const aiAssistBox = $('#aiAssistBox');
  const aiCategoryVal = $('#aiCategoryVal');
  const aiToneVal = $('#aiToneVal');
  const aiDeptVal = $('#aiDeptVal');
  const aiQualityScore = $('#aiQualityScore');
  const aiCategoryTag = $('#aiCategoryTag');
  const aiDuplicateAlert = $('#aiDuplicateAlert');
  const aiDuplicateList = $('#aiDuplicateList');

  const key = 'campusVoiceDraftV7';
  const types = {
    Issue: ['Write like a useful incident report.', 'Mention what happened, where it happened, how often it occurs and what it affected.'],
    Suggestion: ['Make the idea easy to evaluate.', 'Explain the improvement, why it helps and what a practical first step could be.'],
    Appreciation: ['Give specific credit.', 'Mention what was done well and why it made a positive difference.']
  };

  const saveDraft = () => {
    const data = {};
    new FormData(form).forEach((v, k) => { if (k !== 'image' && k !== 'csrf_token') data[k] = v; });
    try {
      localStorage.setItem(key, JSON.stringify(data));
      if (draftState) draftState.textContent = 'Draft saved on this device · ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (_) {}
  };

  const updateType = () => {
    const selected = $$('input[name="submission_type"]', form).find(x => x.checked)?.value || 'Issue';
    $$('.type-option', form).forEach(x => x.classList.toggle('selected', !!$('input', x)?.checked));
    const [title, hint] = types[selected] || types.Issue;
    if ($('#dynamicTitle')) $('#dynamicTitle').textContent = title;
    if ($('#dynamicHint')) $('#dynamicHint').textContent = hint;
    triggerAIAssist();
    saveDraft();
  };

  let assistTimeout = null;
  let predictedCategory = "";

  const triggerAIAssist = () => {
    clearTimeout(assistTimeout);
    assistTimeout = setTimeout(async () => {
      const text = desc.value.trim();
      if (text.length < 10) {
        if (aiCategoryVal) aiCategoryVal.textContent = "—";
        if (aiToneVal) aiToneVal.textContent = "—";
        if (aiDeptVal) aiDeptVal.textContent = "—";
        if (aiQualityScore) aiQualityScore.textContent = "Type more details for AI assist...";
        if (aiDuplicateAlert) aiDuplicateAlert.hidden = true;
        return;
      }

      const submission_type = $$('input[name="submission_type"]', form).find(x => x.checked)?.value || 'Issue';

      try {
        const res = await fetch('/api/assist', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ description: text, submission_type: submission_type })
        });
        if (!res.ok) return;
        const data = await res.json();

        predictedCategory = data.category;
        if (aiCategoryVal) aiCategoryVal.textContent = data.category + (data.confidence > 0 ? ` (${data.confidence}%)` : "");
        if (aiToneVal) aiToneVal.textContent = data.emotion || data.sentiment;
        if (aiDeptVal) aiDeptVal.textContent = data.department;

        if (aiQualityScore && data.quality) {
          aiQualityScore.textContent = `${data.quality.badge} · Score ${data.quality.score}/100`;
          if (data.quality.hint) quality.textContent = data.quality.hint;
        }

        // Show duplicates if any
        if (aiDuplicateAlert && aiDuplicateList) {
          if (data.similar_matches && data.similar_matches.length > 0) {
            aiDuplicateList.innerHTML = data.similar_matches.map(m => `
              <div class="dup-item">
                <span class="dup-badge">${Math.round(m.similarity * 100)}% match</span>
                <span class="dup-desc"><b>${m.category}:</b> ${m.snippet}</span>
                <a class="dup-link" href="/track/${m.public_code}" target="_blank">View ↗</a>
              </div>
            `).join('');
            aiDuplicateAlert.hidden = false;
          } else {
            aiDuplicateAlert.hidden = true;
          }
        }
      } catch (e) {
        // Degrade gracefully
      }
    }, 380);
  };

  // Clicking on category recommendation applies it
  if (aiCategoryTag && categorySelect) {
    aiCategoryTag.addEventListener('click', () => {
      if (!predictedCategory || predictedCategory === "General" || predictedCategory === "—") return;
      for (let i = 0; i < categorySelect.options.length; i++) {
        if (categorySelect.options[i].value === predictedCategory) {
          categorySelect.selectedIndex = i;
          categorySelect.dispatchEvent(new Event('change'));
          aiCategoryTag.classList.add('applied');
          setTimeout(() => aiCategoryTag.classList.remove('applied'), 1000);
          break;
        }
      }
    });
  }

  const update = () => {
    const n = desc.value.length;
    count.textContent = n;
    if (n > 0) {
      quality.textContent = n < 10 ? 'Add at least 10 characters.' : n < 70 ? 'Good start. Mention the specific location or effect.' : n < 150 ? 'Clear context. A desired outcome makes this stronger.' : 'Detailed report. Clear and actionable for administration.';
    } else quality.textContent = 'A clear description helps the right department understand and act quickly.';
    count.parentElement?.classList.toggle('near-limit', n > 1450);

    const fields = $$('input,select,textarea', form).filter(x => !['file', 'hidden', 'checkbox'].includes(x.type) && x.name !== 'student_name');
    let done = 0, total = fields.length;
    fields.forEach(x => { if (x.type === 'radio') return; if (x.value.trim()) done++; });
    if ($$('input[name="submission_type"]:checked', form).length) done++;
    total += 1;
    const pct = Math.min(100, Math.round(done / Math.max(total, 1) * 100));
    bar.style.width = pct + '%';
    progressText.textContent = pct + '% complete';
    
    triggerAIAssist();
    saveDraft();
  };

  const restore = () => {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data.description) return;
      if (window.confirm('Restore your unfinished Campus Voice draft?')) {
        Object.entries(data).forEach(([k, v]) => {
          const el = form.elements[k];
          if (!el) return;
          if (el instanceof RadioNodeList) [...el].forEach(r => r.checked = r.value === v);
          else if (el.type === 'checkbox') el.checked = v === 'on' || v === true;
          else el.value = v;
        });
        if (nameField && anon) nameField.disabled = anon.checked;
        updateType();
        update();
        if (draftState) draftState.textContent = 'Draft restored.';
      }
    } catch (_) {}
  };

  $$('input[name="submission_type"]', form).forEach(x => x.addEventListener('change', updateType));
  $$('input,select,textarea', form).forEach(x => x.addEventListener(x.tagName === 'TEXTAREA' ? 'input' : 'change', update));
  anon?.addEventListener('change', () => {
    nameField.disabled = anon.checked;
    if (anon.checked) nameField.value = '';
    update();
  });

  file?.addEventListener('change', () => {
    preview.innerHTML = '';
    preview.classList.add('hidden');
    const f = file.files[0];
    if (!f) return;
    if (f.size > 5 * 1024 * 1024 || !/^image\/(png|jpeg|webp)$/.test(f.type)) {
      preview.textContent = 'Choose a PNG, JPG or WEBP image under 5 MB.';
      preview.classList.remove('hidden');
      file.value = '';
      return;
    }
    const img = document.createElement('img');
    img.src = URL.createObjectURL(f);
    img.alt = 'Evidence preview';
    img.onload = () => URL.revokeObjectURL(img.src);
    const label = document.createElement('span');
    label.textContent = f.name;
    preview.append(img, label);
    preview.classList.remove('hidden');
    update();
  });

  form.addEventListener('submit', e => {
    if (desc.value.trim().length < 10) {
      e.preventDefault();
      desc.focus();
      return;
    }
    try { localStorage.removeItem(key); } catch (_) {}
  });

  restore();
  update();
})();
