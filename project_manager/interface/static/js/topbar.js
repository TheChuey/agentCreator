/* Shared topbar navigation

   Home / Editor / Chat must sit in the same place on every page, so
   the markup and styling live here instead of being copied into each
   page. Each page marks its header with data-pm-header and calls
   initTopbar({ page }).

   The links are rendered as anchors, not buttons, on purpose: home
   and editor apply a bare `button { ... }` rule and chat.html styles
   `.btn-header`, so anchors sidestep both stylesheets and come out
   pixel-identical on all three pages. An item flagged `popup` is the
   one exception - it has to be a real button to be operable, so
   .pmnav-button undoes the host pages' button styling instead. */

const NAV_ITEMS = [
  { page: 'home', label: 'Home', href: '/' },
  { page: 'editor', label: 'Editor', href: '/editor' },
  { page: 'chat', label: 'Chat', href: '/chat' },
  {
    page: 'prompt-builder',
    label: 'Prompt Builder',
    href: '/prompt-builder',
    popup: { name: 'PMPromptBuilder', width: 1100, height: 760 }
  },
  { page: 'test', label: 'Test', href: '/test' }
];

const STYLE_ID = 'pmnav-style';

const NAV_CSS = `
.pmnav {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  flex-shrink: 0;
}

.pmnav-link {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #45474d;
  background: #2f3136;
  color: #e5e7eb;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.pmnav-link:hover {
  background: #3a3d44;
  border-color: #565a61;
  color: #ffffff;
}

.pmnav-link.pmnav-current,
.pmnav-link[aria-current="page"] {
  background: #0e639c;
  border-color: #1177bb;
  color: #ffffff;
}

.pmnav-link:focus-visible {
  outline: 2px solid #4fc3f7;
  outline-offset: 2px;
}

/* A popup item has to be a <button> to be clickable, which means it
   inherits whatever bare button rule the host page applies. These
   declarations put it back in line with the anchors. */

.pmnav-link.pmnav-button {
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
  cursor: pointer;
}
`;

/* Tools open in their own centred window. A named target means a
   second click reuses the window instead of stacking duplicates, the
   same way the agent cards open chat. */
function openPopup(url, spec) {
  const left = Math.max(0, (window.screen.width - spec.width) / 2);
  const top = Math.max(0, (window.screen.height - spec.height) / 2);
  const popup = window.open(
    url,
    spec.name,
    `width=${spec.width},height=${spec.height},top=${top},left=${left},` +
    'resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no'
  );
  if (!popup) {
    window.alert('The popup was blocked. Allow popups for this site and try again.');
  }
  return popup;
}

function ensureStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = NAV_CSS;
  document.head.appendChild(style);
}

function initTopbar(options = {}) {
  const page = options.page;
  const header = options.header
    || document.querySelector('[data-pm-header]');
  if (!header) return null;

  ensureStyle();

  /* Re-initialising must not stack duplicate nav groups. */
  for (const child of Array.from(header.children)) {
    if (child.classList && child.classList.contains('pmnav')) {
      child.remove();
    }
  }

  const nav = document.createElement('nav');
  nav.className = 'pmnav';
  nav.setAttribute('aria-label', 'Main');

  for (const item of NAV_ITEMS) {

    if (item.popup) {
      const trigger = document.createElement('button');
      trigger.type = 'button';
      trigger.className = 'pmnav-link pmnav-button';
      trigger.textContent = item.label;
      trigger.title = 'Opens in a new window';
      trigger.addEventListener('click', () => openPopup(item.href, item.popup));
      nav.appendChild(trigger);
      continue;
    }

    const link = document.createElement('a');
    link.className = 'pmnav-link';
    link.href = item.href;
    link.textContent = item.label;
    if (item.page === page) {
      link.classList.add('pmnav-current');
      link.setAttribute('aria-current', 'page');
    }
    nav.appendChild(link);
  }

  header.appendChild(nav);
  return nav;
}

export { initTopbar, openPopup, NAV_ITEMS };
