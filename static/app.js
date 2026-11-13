// Theme toggle (persisted)
(function () {
  const root = document.documentElement;
  let saved = null;
  try { saved = localStorage.getItem('theme'); } catch (e) {}
  if (!saved && window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches) saved = 'dark';
  if (saved) root.setAttribute('data-theme', saved);
})();

document.addEventListener('DOMContentLoaded', () => {
  const root = document.documentElement;
  const tbtn = document.getElementById('theme-toggle');
  const paint = () => { if (tbtn) tbtn.textContent = root.getAttribute('data-theme') === 'dark' ? '☀️' : '🌙'; };
  paint();
  if (tbtn) tbtn.addEventListener('click', () => {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) {}
    paint();
  });

  const mt = document.getElementById('menu-toggle');
  if (mt) mt.addEventListener('click', () => {
    const sb = document.querySelector('.sidebar');
    (sb || document.querySelector('.nav-links')).classList.toggle('open');
    document.querySelector('.nav-links').classList.toggle('open');
  });

  // Live filter: <input data-filter="#tableId tbody tr, .card-selector">
  document.querySelectorAll('[data-filter]').forEach(input => {
    input.addEventListener('input', () => {
      const q = input.value.trim().toLowerCase();
      document.querySelectorAll(input.dataset.filter).forEach(el => {
        el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
      const counter = document.querySelector(input.dataset.count || '#none');
      if (counter) counter.textContent = document.querySelectorAll(input.dataset.filter + ':not([style*="none"])').length;
    });
  });

  // Specialty pills filter doctor cards
  document.querySelectorAll('.pill[data-spec]').forEach(p => p.addEventListener('click', () => {
    document.querySelectorAll('.pill[data-spec]').forEach(x => x.classList.remove('active'));
    p.classList.add('active');
    const s = p.dataset.spec;
    document.querySelectorAll('.doc-card[data-spec]').forEach(c => {
      c.style.display = (s === 'all' || c.dataset.spec === s) ? '' : 'none';
    });
  }));

  // Declarative validation: <input data-rule="letters|phone|age|password|posint|nonneg">
  const rules = {
    letters: [v => /^[A-Za-z ]+$/.test(v), 'Letters and spaces only.'],
    phone:   [v => /^[6-9]\d{9}$/.test(v), 'Enter a valid 10-digit mobile number.'],
    age:     [v => Number(v) >= 1 && Number(v) <= 120, 'Enter a valid age (1–120).'],
    password:[v => v.length >= 6 && v.length <= 10, 'Password must be 6–10 characters.'],
    posint:  [v => /^\d+$/.test(v) && Number(v) > 0, 'Must be a positive whole number.'],
    nonneg:  [v => /^\d+$/.test(v), 'Must be a non-negative whole number.'],
  };
  document.querySelectorAll('form.validate').forEach(form => {
    form.addEventListener('submit', e => {
      let ok = true;
      form.querySelectorAll('[data-rule]').forEach(inp => {
        const [test, msg] = rules[inp.dataset.rule];
        const err = inp.closest('.field').querySelector('.field-error');
        const bad = !test(inp.value.trim());
        if (err) err.textContent = bad ? msg : '';
        if (bad) ok = false;
      });
      if (!ok) e.preventDefault();
    });
  });

  // Password reveal
  document.querySelectorAll('.pw-field button').forEach(b => b.addEventListener('click', () => {
    const i = b.parentElement.querySelector('input');
    i.type = i.type === 'password' ? 'text' : 'password';
  }));

  // Dismissible flashes
  document.querySelectorAll('.flash button').forEach(b => b.addEventListener('click', () => b.parentElement.remove()));
});
