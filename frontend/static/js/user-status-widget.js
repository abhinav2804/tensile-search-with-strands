import { USER_STATUS_API_URL, USER_STATUS_POLL_MS, USER_STATUS_AUTO_HIDE_MS, USER_STATUS_ENABLE, USER_STATUS_DEBUG, SHOW_WIDGET_LOGS, ICONS, CLASSNAMES, DISPLAY_FIELDS } from './user-status-config.js';

/**
 * Lightweight user status widget.
 * Injects a floating info card (top-right below existing auth header) and auto-hides.
 * Designed to avoid layout shifts: position fixed & independent.
 */
(function initUserStatusWidget() {
  if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] init invoked');
  if (!USER_STATUS_ENABLE) { if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] USER_STATUS_ENABLE=false – aborting'); return; }
  if (typeof window === 'undefined' || !document) { if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] No window/document – aborting'); return; }
  if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] Environment OK, proceeding with DOM creation');

  const log = (...args) => USER_STATUS_DEBUG && console.debug('[UserStatusWidget]', ...args);

  let pollTimer = null;
  let hideTimer = null;

  // Create container early to avoid flicker
  const container = document.createElement('div');
  container.className = CLASSNAMES.container;
  container.setAttribute('role', 'status');
  container.setAttribute('aria-live', 'polite');
  container.style.cssText = [
    'position:fixed',
    'top:80px',
    'right:1rem',
    'z-index:1600',
    'min-width:240px',
    'max-width:300px',
    'font-family:inherit',
    'background:linear-gradient(145deg, rgba(17,24,39,0.95) 0%, rgba(30,41,59,0.90) 100%)',
    'border:1px solid rgba(139,92,246,0.4)',
    'border-radius:16px',
    'padding:0.9rem 1rem 0.8rem 1rem',
    'box-shadow:0 10px 40px rgba(0,0,0,0.4)',
    'backdrop-filter:blur(20px)',
    'color:#e2e8f0',
    'font-size:0.75rem',
    'line-height:1.3',
    'display:flex',
    'flex-direction:column',
    'gap:0.45rem',
    'opacity:0',
    'transform:translateY(-6px)',
    'transition:opacity .4s ease, transform .4s ease'
  ].join(';');

  const title = document.createElement('div');
  title.style.cssText = 'font-size:0.8rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;white-space:nowrap;';
  const titleIcon = document.createElement('span');
  titleIcon.textContent = '👤';
  const titleText = document.createElement('span');
  titleText.textContent = 'User status';
  title.appendChild(titleIcon); title.appendChild(titleText);
  container.appendChild(title);

  const rowsWrapper = document.createElement('div');
  rowsWrapper.id = 'uswRows';
  rowsWrapper.style.cssText = 'display:flex;flex-direction:column;gap:0.25rem;';
  container.appendChild(rowsWrapper);

  const footer = document.createElement('div');
  footer.style.cssText = 'margin-top:0.2rem;display:flex;justify-content:space-between;align-items:center;font-size:0.65rem;opacity:0.6;';
  const userSpan = document.createElement('span');
  userSpan.id = 'uswUser';
  userSpan.textContent = '';
  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.setAttribute('aria-label', 'Close user status');
  closeBtn.style.cssText = 'background:none;border:0;color:#94a3b8;cursor:pointer;font-size:0.9rem;padding:0 4px;line-height:1;border-radius:4px;';
  closeBtn.textContent = '×';
  closeBtn.addEventListener('click', () => fadeOut(true));
  footer.appendChild(userSpan); footer.appendChild(closeBtn);
  container.appendChild(footer);

  // Inject style overrides class-based (optional usage)
  const styleTag = document.createElement('style');
  styleTag.textContent = `.${CLASSNAMES.fadeOut}{opacity:0!important;transform:translateY(-4px)!important;pointer-events:none}.` +
    `${CLASSNAMES.closing}{transition:opacity .3s ease, transform .3s ease}`;
  document.head.appendChild(styleTag);
  if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] Style tag inserted');

  document.body.appendChild(container);
  if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] Container appended to body with class', CLASSNAMES.container);
  requestAnimationFrame(() => { container.style.opacity = '1'; container.style.transform = 'translateY(0)'; });
  if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] Fade-in requested (rAF queued)');

  function renderRows(data) {
    if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] Rendering rows with data keys:', Object.keys(data || {}));
    rowsWrapper.innerHTML = '';
    DISPLAY_FIELDS.forEach(def => {
      const row = document.createElement('div');
      row.className = CLASSNAMES.row;
      row.style.cssText = 'display:flex;justify-content:space-between;gap:0.6rem;align-items:center;background:rgba(139,92,246,0.08);padding:4px 6px;border-radius:8px;';
      const lbl = document.createElement('span');
      lbl.className = CLASSNAMES.label;
      lbl.style.cssText = 'flex:1;color:#cbd5e1;font-weight:500;';
      lbl.textContent = def.label;
      const val = document.createElement('span');
      val.className = CLASSNAMES.value;
      val.style.cssText = 'min-width:50px;text-align:right;font-weight:600;';
      const raw = data[def.key];
      let ok = false; let display = '';
      switch (def.type) {
        case 'boolean':
          ok = !!raw; display = ok ? ICONS.success : ICONS.fail; break;
        case 'presence':
          ok = typeof raw === 'string' && raw.trim() !== ''; display = ok ? ICONS.success : ICONS.fail; break;
        case 'string-or-cross':
          ok = typeof raw === 'string' && raw.trim() !== ''; display = ok ? raw : ICONS.fail; break;
        default:
          display = raw == null ? ICONS.fail : String(raw);
      }
      if (def.type !== 'string-or-cross') {
        val.style.color = ok ? '#4ade80' : '#f87171';
      } else if (!ok) {
        val.style.color = '#f87171';
      }
      val.textContent = display;
      row.appendChild(lbl); row.appendChild(val);
      rowsWrapper.appendChild(row);
    });
  }

  function setUserLine(data) {
    const user = data.email || data.userId || 'Unknown user';
    userSpan.textContent = user.length > 18 ? user.slice(0,15) + '…' : user;
    userSpan.title = user;
  }

  async function fetchStatus() {
    if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] fetchStatus() start');
    try {
      log('Fetching status from', USER_STATUS_API_URL);
      const res = await fetch(USER_STATUS_API_URL, { credentials: 'include' });
      if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] Fetch response status:', res.status);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const json = await res.json();
      if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] Parsed JSON:', json);
      log('Response', json);
      renderRows(json);
      setUserLine(json);
      scheduleHide();
    } catch (err) {
      log('Fetch failed', err);
      if (SHOW_WIDGET_LOGS) console.warn('[UserStatusWidget] Fetch failed -> fallback UI. Error:', err);
      // Show fallback rows with crosses
      const fallback = DISPLAY_FIELDS.reduce((acc, f) => { acc[f.key] = null; return acc; }, {});
      fallback.login = false;
      renderRows(fallback);
      setUserLine({ userId: 'Not authenticated' });
      scheduleHide();
    }
    if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] fetchStatus() end');
  }

  function scheduleHide() {
    if (USER_STATUS_AUTO_HIDE_MS <= 0) return; // disabled
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => fadeOut(false), USER_STATUS_AUTO_HIDE_MS);
    if (SHOW_WIDGET_LOGS) console.log(`[UserStatusWidget] Auto-hide scheduled in ${USER_STATUS_AUTO_HIDE_MS}ms`);
  }

  function fadeOut(manual) {
    if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] fadeOut called. manual=', manual);
    container.classList.add(CLASSNAMES.closing);
    container.style.opacity = '0';
    container.style.transform = 'translateY(-4px)';
    setTimeout(() => {
      if (container.parentNode) container.parentNode.removeChild(container);
      if (pollTimer) clearInterval(pollTimer);
      log('Widget removed', manual ? '(manual close)' : '(auto hide)');
      if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] Container removed from DOM');
    }, 350);
  }

  if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] Initiating first fetch');
  fetchStatus();
  if (USER_STATUS_POLL_MS && USER_STATUS_POLL_MS > 500) {
    pollTimer = setInterval(fetchStatus, USER_STATUS_POLL_MS);
    if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] Polling enabled every', USER_STATUS_POLL_MS, 'ms');
  }
  if (SHOW_WIDGET_LOGS) console.log('[UserStatusWidget] Initialization complete');
})();
