(() => {
  const body = document.body, theme = document.getElementById('themeToggle'), menu = document.getElementById('mobileMenu'), sidebar = document.getElementById('sidebar');
  if (localStorage.getItem('cvTheme') === 'dark') body.classList.add('dark-admin');
  theme?.addEventListener('click', () => { body.classList.toggle('dark-admin'); localStorage.setItem('cvTheme', body.classList.contains('dark-admin') ? 'dark' : 'light'); });
  menu?.addEventListener('click', () => { const open = sidebar?.classList.toggle('open'); menu.setAttribute('aria-expanded', open ? 'true' : 'false'); });
  sidebar?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => { sidebar.classList.remove('open'); menu?.setAttribute('aria-expanded','false'); }));
  const toast = document.getElementById('toast');
  window.showToast = msg => { if (!toast) return; toast.textContent = msg; toast.classList.add('show'); clearTimeout(window._toast); window._toast=setTimeout(()=>toast.classList.remove('show'),2300); };
})();
