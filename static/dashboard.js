(() => {
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const statusMap = {
    All: ['All', 'New', 'Reviewing', 'In Progress', 'Resolved', 'Implemented'],
    Issue: ['All', 'New', 'Reviewing', 'In Progress', 'Resolved'],
    Suggestion: ['All', 'New', 'Under Review', 'Planned', 'Implemented', 'Declined'],
    Appreciation: ['All', 'New', 'Acknowledged']
  };
  let state = {
    type: 'All', department: 'All', category: 'All', priority: 'All',
    status: 'All', search: '', date_range: 'All'
  };
  let requestSeq = 0;
  const commonStatuses = ['New', 'Reviewing', 'In Progress', 'Resolved', 'Under Review', 'Planned', 'Implemented', 'Declined', 'Acknowledged'];

  const syncStatusOptions = () => {
    const select = $('filterStatus');
    if (!select) return;
    const current = select.value, options = statusMap[state.type] || statusMap.All;
    select.innerHTML = options.map(x => `<option>${esc(x)}</option>`).join('');
    select.value = options.includes(current) ? current : 'All';
    state.status = select.value;
  };

  const params = () => {
    const p = new URLSearchParams();
    Object.entries(state).forEach(([k, v]) => p.set(k, v));
    return p.toString();
  };

  const updateExport = () => {
    if ($('exportLink')) $('exportLink').href = '/export.csv?' + params();
  };

  const counter = (el, target, value) => {
    if (!el) return;
    const end = Number(value) || 0;
    const start = Number(el.dataset.value || 0);
    el.dataset.value = end;
    const startTime = performance.now();
    const tick = now => {
      const t = Math.min(1, (now - startTime) / 500), eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(start + (end - start) * eased);
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  function bars(el, data) {
    if (!el) return;
    el.innerHTML = '';
    const entries = Object.entries(data || {}).sort((a, b) => b[1] - a[1]).slice(0, 6);
    if (!entries.length) {
      el.innerHTML = '<div class="table-loading">No data in this view.</div>';
      return;
    }
    const max = Math.max(...entries.map(x => x[1]), 1);
    entries.forEach(([name, val], i) => {
      const r = document.createElement('div');
      r.className = 'h-row';
      r.style.animationDelay = `${i * 45}ms`;
      r.innerHTML = `<span title="${esc(name)}">${esc(name)}</span><div class="h-track"><i style="width:${Math.max(4, val / max * 100)}%"></i></div><b>${val}</b>`;
      el.appendChild(r);
    });
  }

  function trend(data) {
    const el = $('trendChart');
    if (!el) return;
    el.innerHTML = '';
    const entries = Object.entries(data || {});
    if (!entries.length) {
      el.innerHTML = '<div class="table-loading">No activity in this period.</div>';
      return;
    }
    const max = Math.max(...entries.map(x => x[1]), 1);
    entries.forEach(([day, val], i) => {
      const b = document.createElement('div');
      b.className = 'chart-bar';
      b.style.height = Math.max(8, val / max * 88) + '%';
      b.style.animationDelay = `${i * 35}ms`;
      b.innerHTML = `<b>${val}</b><span>${esc(day.slice(5))}</span>`;
      el.appendChild(b);
    });
  }

  function attention(items) {
    const actionable = (items || []).filter(x => x.submission_type === 'Issue' && x.status !== 'Resolved').sort((a, b) => b.attention_score - a.attention_score).slice(0, 4);
    const box = document.getElementById('attentionList');
    if (!box) return;
    box.innerHTML = actionable.length ? actionable.map((x, i) => `
      <a class="attention-item" href="/submission/${x.id}">
        <span class="attention-index">0${i + 1}</span>
        <div><b>${esc(x.category)}</b><small>${esc(x.location || 'No location')} · ${esc(x.public_code)}</small></div>
        <span class="priority-badge priority-${esc(String(x.priority || 'none').toLowerCase())}">${esc(x.priority)}</span>
        <span class="attention-arrow">→</span>
      </a>
    `).join('') : '<div class="empty-card"><span>✓</span><h2>Nothing urgent.</h2><p>No unresolved issue needs immediate attention in this view.</p></div>';
  }

  function row(x) {
    const initials = esc((x.category || 'CV').split(/\s+/).map(s => s[0]).join('').slice(0, 2).toUpperCase());
    const slaClass = x.sla_class || 'sla-ok';
    const slaLabel = x.sla_label || 'Standard SLA';
    const dept = x.department || 'General';
    return `<tr>
      <td><input class="row-check" type="checkbox" value="${x.id}" data-submission-type="${esc(x.submission_type)}" aria-label="Select ${esc(x.public_code)}"></td>
      <td>
        <a class="submission-cell" href="/submission/${x.id}">
          <span class="submission-avatar">${initials}</span>
          <span><b>${esc(x.category)}</b><small>${esc(x.public_code)} · ${esc(x.location || 'Campus')}</small></span>
        </a>
      </td>
      <td><span class="dept-tag">${esc(dept)}</span></td>
      <td><span class="type-pill type-${esc(x.submission_type.toLowerCase())}">${esc(x.submission_type)}</span></td>
      <td><span class="signal-label">${esc(x.signal_label || 'Routine')}</span></td>
      <td>${x.submission_type === 'Issue' ? `<span class="priority-badge priority-${esc(String(x.priority).toLowerCase())}">${esc(x.priority)}</span>` : '<span class="priority-badge priority-none">—</span>'}</td>
      <td><span class="sla-pill ${esc(slaClass)}">${esc(slaLabel)}</span></td>
      <td><span class="status-pill status-${esc(x.status.toLowerCase().replace(/\s+/g, '-'))}">${esc(x.status)}</span></td>
      <td>${Number(x.age_days || 0).toFixed(x.age_days < 1 ? 1 : 0)}d</td>
      <td><a href="/submission/${x.id}" aria-label="Open ${esc(x.public_code)}">→</a></td>
    </tr>`;
  }

  async function load() {
    const seq = ++requestSeq;
    const body = $('inboxBody');
    if (!body.dataset.loaded) body.innerHTML = '<tr><td colspan="10" class="table-loading"><span class="spinner"></span> Loading records…</td></tr>';
    try {
      const r = await fetch('/api/dashboard?' + params(), {
        cache: 'no-store',
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.error || `Request failed (${r.status})`);
      if (seq !== requestSeq) return;

      counter($('kTotal'), 0, d.total);
      counter($('kOpen'), 0, d.open_issues);
      counter($('kHigh'), 0, d.high_priority);
      if ($('kRate')) $('kRate').textContent = d.resolution_rate == null ? '—' : d.resolution_rate + '%';
      if ($('kTotalSub')) $('kTotalSub').textContent = d.total === d.unfiltered_total ? 'All submissions' : `Filtered from ${d.unfiltered_total}`;
      if ($('generatedAt')) $('generatedAt').textContent = 'Updated ' + new Date(d.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      trend(d.trend);
      bars($('categoryBars'), d.category_data || {});
      attention(d.attention_items || d.submissions);

      const em = d.emerging_signal || {};
      if ($('emergingName')) $('emergingName').textContent = em.name || 'No emerging signal';
      if ($('emergingGrowth')) $('emergingGrowth').textContent = (em.growth || 0) + '%';
      if ($('emergingRecent')) $('emergingRecent').textContent = em.recent || 0;
      if ($('trendDirection')) $('trendDirection').textContent = d.trend_delta?.direction === 'up' ? 'Rising' : d.trend_delta?.direction === 'down' ? 'Cooling' : 'Stable';
      if ($('emergingText')) $('emergingText').textContent = em.recent ? `${em.name} has ${em.recent} reports in the last 7 days versus ${em.prior || 0} in the previous 7 days.` : 'Not enough recent data to identify an emerging category.';

      const action = (d.attention_items || [])[0];
      if ($('actionTitle')) $('actionTitle').textContent = action ? `${action.category} · ${action.priority} priority` : 'Queue is clear';
      if ($('actionText')) $('actionText').textContent = action ? `${action.signal_label} · ${action.location || 'Location not provided'} · ${action.similar_count || 0} related signal(s).` : 'There are no unresolved issue records requiring action in this view.';
      if ($('actionLink')) $('actionLink').href = action ? `/submission/${action.id}` : '/issues';

      const visible = [...(d.submissions || [])].sort((a, b) => (b.attention_score || 0) - (a.attention_score || 0));
      if ($('resultCount')) $('resultCount').textContent = `Showing ${Math.min(visible.length, d.total)} of ${d.total} matching submissions · highest attention first`;
      body.innerHTML = visible.length ? visible.map(row).join('') : '<tr><td colspan="10" class="table-loading">No submissions match these filters.</td></tr>';
      body.dataset.loaded = '1';

      if ($('selectAll')) $('selectAll').checked = false;
      syncBulkOptions();
      updateExport();
    } catch (e) {
      if (seq !== requestSeq) return;
      body.innerHTML = '<tr><td colspan="10" class="table-loading">Unable to refresh this view. <button class="inline-retry" id="retryNow">Retry</button></td></tr>';
      $('retryNow')?.addEventListener('click', load);
      if (typeof showToast === 'function') showToast(e.message || 'Dashboard could not be refreshed');
    }
  }

  function syncBulkOptions() {
    const selected = [...document.querySelectorAll('.row-check:checked')];
    const select = $('bulkStatus');
    if (!select) return;
    const cur = select.value;
    if (!selected.length) {
      select.innerHTML = '<option value="">Select records first</option>';
      select.value = '';
      return;
    }
    const common = selected.map(x => statusMap[x.dataset.submissionType] || ['All']).reduce((a, b) => a.filter(v => b.includes(v)), commonStatuses);
    select.innerHTML = '<option value="">Bulk status</option>' + common.filter(v => v !== 'All').map(v => `<option>${esc(v)}</option>`).join('');
    if (common.includes(cur)) select.value = cur;
  }

  function sync() {
    state = {
      type: $('filterType') ? $('filterType').value : 'All',
      department: $('filterDepartment') ? $('filterDepartment').value : 'All',
      category: $('filterCategory') ? $('filterCategory').value : 'All',
      priority: $('filterPriority') ? $('filterPriority').value : 'All',
      status: $('filterStatus') ? $('filterStatus').value : 'All',
      search: $('filterSearch') ? $('filterSearch').value.trim() : '',
      date_range: $('filterRange') ? $('filterRange').value : 'All'
    };
    syncStatusOptions();
    load();
  }

  ['filterType', 'filterDepartment', 'filterCategory', 'filterPriority', 'filterStatus', 'filterRange'].forEach(id => {
    if ($(id)) $(id).addEventListener('change', sync);
  });
  if ($('filterSearch')) $('filterSearch').addEventListener('input', () => {
    clearTimeout(window._searchT);
    window._searchT = setTimeout(sync, 280);
  });
  if ($('clearFilters')) $('clearFilters').addEventListener('click', () => {
    ['filterType', 'filterDepartment', 'filterCategory', 'filterPriority', 'filterStatus', 'filterRange'].forEach(id => {
      if ($(id)) $(id).value = 'All';
    });
    if ($('filterSearch')) $('filterSearch').value = '';
    sync();
  });
  if ($('refreshBtn')) $('refreshBtn').addEventListener('click', load);
  if ($('selectAll')) $('selectAll').addEventListener('change', e => {
    document.querySelectorAll('.row-check').forEach(x => x.checked = e.target.checked);
    syncBulkOptions();
  });
  document.addEventListener('change', e => {
    if (e.target.classList.contains('row-check')) syncBulkOptions();
  });

  if ($('applyBulk')) $('applyBulk').addEventListener('click', async () => {
    const status = $('bulkStatus').value, ids = [...document.querySelectorAll('.row-check:checked')].map(x => x.value);
    if (!status || !ids.length) return typeof showToast === 'function' ? showToast('Select records and a compatible status first.') : alert('Select records first');
    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    const r = await fetch('/api/bulk-status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token || '' },
      credentials: 'same-origin',
      body: JSON.stringify({ ids, status })
    });
    const d = await r.json();
    if (!r.ok) return typeof showToast === 'function' ? showToast(d.error || 'Bulk update failed.') : alert('Update failed');
    if (typeof showToast === 'function') showToast(`${d.updated || 0} record(s) updated`);
    load();
  });

  if ($('globalSearch')) $('globalSearch').addEventListener('input', e => {
    if ($('filterSearch')) $('filterSearch').value = e.target.value;
    clearTimeout(window._globalT);
    window._globalT = setTimeout(sync, 280);
  });

  window.addEventListener('keydown', e => {
    if (e.key === '/' && ['INPUT', 'TEXTAREA', 'SELECT'].indexOf(document.activeElement.tagName) < 0) {
      e.preventDefault();
      if ($('globalSearch')) $('globalSearch').focus();
    }
  });

  sync();
  setInterval(load, 60000);
})();
