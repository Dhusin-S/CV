(() => {
  'use strict';
  const list = document.getElementById('queueList');
  const search = document.getElementById('queueSearch');
  const dept = document.getElementById('queueDepartment');
  const priority = document.getElementById('queuePriority');
  const status = document.getElementById('queueStatus');
  const sla = document.getElementById('queueSLA');
  const age = document.getElementById('queueAge');
  const clear = document.getElementById('queueClear');
  const refresh = document.getElementById('queueRefresh');
  const empty = document.getElementById('queueNoResults');
  if (!list || !search || !priority || !status || !age || !clear || !refresh) return;

  const items = () => [...list.querySelectorAll('.queue-item')];
  const apply = () => {
    const q = search.value.trim().toLowerCase();
    const d = dept ? dept.value : 'All';
    const p = priority.value;
    const s = status.value;
    const slaVal = sla ? sla.value : 'All';
    const minAge = Number(age.value || 0);
    let visible = 0;

    items().forEach((el) => {
      const haystack = (el.dataset.search || '').toLowerCase();
      const matchDept = (d === 'All' || el.dataset.department === d);
      const matchSla = (slaVal === 'All' || el.dataset.sla === slaVal);
      const ok = (!q || haystack.includes(q)) &&
        matchDept &&
        matchSla &&
        (p === 'All' || el.dataset.priority === p) &&
        (s === 'All' || el.dataset.status === s) &&
        (!minAge || Number(el.dataset.age || 0) >= minAge);

      el.hidden = !ok;
      if (ok) {
        visible += 1;
        const rank = el.querySelector('.queue-rank');
        if (rank) rank.textContent = String(visible).padStart(2, '0');
        el.style.animationDelay = `${Math.min(visible * 35, 350)}ms`;
      }
    });
    if (empty) empty.hidden = visible !== 0;
  };

  [search, dept, priority, status, sla, age].filter(Boolean).forEach((el) => {
    el.addEventListener(el === search ? 'input' : 'change', apply);
  });

  clear.addEventListener('click', () => {
    search.value = '';
    if (dept) dept.value = 'All';
    priority.value = 'All';
    status.value = 'All';
    if (sla) sla.value = 'All';
    age.value = 'All';
    apply();
    search.focus();
  });

  refresh.addEventListener('click', () => {
    refresh.disabled = true;
    refresh.classList.add('is-refreshing');
    window.location.reload();
  });

  apply();
})();
