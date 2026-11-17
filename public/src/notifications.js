// Notifications page (US-14 / FR-23): every notification the user has had, newest first.
// New ones also pop up for a few seconds on whatever page they happened on (see common.js).
let allNotes = [];
let filter = 'all';
const noteList = document.querySelector('#note-list');

const FILTERS = {
  all: () => true,
  unread: (n) => !n.is_read,
  action: (n) => n.needs_action,
  problems: (n) => ['ERROR', 'LOAN_LIMIT', 'HOLD_LIMIT', 'HOLD_EXPIRED'].includes(n.type),
};

// "Today", "Yesterday" or a date, in Toronto time
function dayLabel(value) {
  const fmt = (ms) => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(ms));
  const day = fmt(utcMillis(value));
  if (day === fmt(Date.now())) return 'Today';
  if (day === fmt(Date.now() - 86400000)) return 'Yesterday';
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', weekday: 'long', month: 'long', day: 'numeric' }).format(new Date(utcMillis(value)));
}

// "just now", "5 minutes ago", "3 hours ago"
function howLongAgo(value) {
  const mins = Math.floor((Date.now() - utcMillis(value)) / 60000);
  if (!Number.isFinite(mins) || mins < 1) return 'just now';
  if (mins < 60) return `${mins} minute${mins === 1 ? '' : 's'} ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

function actionLink(note) {
  if (note.type === 'HOLD_READY' || note.type === 'HOLD_WINDOW_CLOSING') return '<a class="note-link" href="holds.html">Go to Holds</a>';
  if (note.type === 'LOAN_DUE_SOON' || note.type === 'BORROW_SUCCESS') return '<a class="note-link" href="personal-library.html">Go to Personal Library</a>';
  if (note.literature_id) return `<a class="note-link" href="literature.html?id=${encodeURIComponent(note.literature_id)}">View book</a>`;
  return '';
}

function drawNotes() {
  const shown = allNotes.filter(FILTERS[filter]);
  const unread = allNotes.filter((n) => !n.is_read).length;
  document.querySelector('#unread-count').textContent = unread ? `(${unread})` : '';
  document.querySelector('#mark-all-read').disabled = unread === 0;
  document.querySelector('#empty-notes').hidden = shown.length > 0;
  document.querySelector('#empty-notes').textContent = allNotes.length
    ? 'No notifications match this filter.'
    : 'Nothing here yet. Borrowing, returning and holds will show up here.';
  noteList.innerHTML = '';
  let lastDay = null;
  for (const note of shown) {
    const day = dayLabel(note.created_at);
    if (day !== lastDay) {
      const heading = document.createElement('h2');
      heading.className = 'note-day';
      heading.textContent = day;
      noteList.appendChild(heading);
      lastDay = day;
    }
    const item = document.createElement('article');
    item.className = `note-item ${noteKindClass(note.type)}${note.is_read ? '' : ' unread'}`;
    item.innerHTML = `
      <span class="note-dot" aria-hidden="true"></span>
      <div class="note-body">
        <div class="note-top">
          <strong>${safeText(note.title)}</strong>
          <time title="${safeText(torontoTime(note.created_at))}">${safeText(howLongAgo(note.created_at))} · ${safeText(torontoTime(note.created_at))}</time>
        </div>
        <p>${safeText(note.message)}</p>
        <div class="note-actions">
          ${actionLink(note)}
          ${note.is_read ? '' : '<button type="button" class="note-read">Mark as read</button>'}
        </div>
      </div>`;
    const readBtn = item.querySelector('.note-read');
    if (readBtn) readBtn.onclick = () => markRead(note);
    noteList.appendChild(item);
  }
}

async function loadNotes() {
  try {
    const data = await libraryRequest('notifications');
    allNotes = data.notifications;
    setBadge(data.unread);
    drawNotes();
  } catch (error) {
    showPageError(error);
  }
}

async function markRead(note) {
  try {
    const data = await libraryRequest(`notifications/${note.notification_id}/read`, { method: 'POST' });
    note.is_read = true;
    setBadge(data.unread);
    drawNotes();
  } catch (error) {
    showPageError(error);
  }
}

document.querySelector('#mark-all-read').onclick = async () => {
  try {
    await libraryRequest('notifications/read', { method: 'POST' });
    allNotes.forEach((n) => { n.is_read = true; });
    setBadge(0);
    drawNotes();
  } catch (error) {
    showPageError(error);
  }
};

document.querySelectorAll('.note-filter').forEach((button) => {
  button.onclick = () => {
    filter = button.dataset.filter;
    document.querySelectorAll('.note-filter').forEach((b) => {
      b.classList.toggle('active', b === button);
      b.setAttribute('aria-selected', String(b === button));
    });
    drawNotes();
  };
});

// common.js found new ones: on this page they go straight into the list instead of popping up
document.addEventListener('udbs:notifications', loadNotes);

(async () => {
  try {
    await checkLogin();
    document.querySelector('#private-content').hidden = false;
    await loadNotes();
    setInterval(() => { if (!document.hidden) drawNotes(); }, 60000); // keeps "5 minutes ago" current
  } catch (error) {
    showPageError(error);
  }
})();
