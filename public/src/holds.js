// Holds page (US-11), accept or decline an offer (US-12) and cancel a hold (US-13)
let holds = [];
const holdList = document.querySelector('#my-holds');

function drawHolds() {
  holdList.innerHTML = '';
  document.querySelector('#hold-count').textContent = holds.length + ' active ' + (holds.length === 1 ? 'hold' : 'holds');
  document.querySelector('#empty-holds').hidden = holds.length > 0;

  for (const hold of holds) {
    const col = document.createElement('div');
    col.className = 'col-md-6 col-lg-4';
    const ready = hold.status === 'READY';
    const details = ready
      ? `<p class="hold-status ready">Ready for you</p>
         <p>Decide by: ${safeText(torontoTime(hold.decision_deadline))}</p>
         <p class="time-left">${timeLeftUntil(hold.decision_deadline)} left to accept</p>`
      : `<p class="hold-status">Waiting · #${safeText(hold.queue_position)} of ${safeText(hold.queue_length)} in line</p>
         <p>Placed: ${safeText(torontoTime(hold.placed_at))}</p>`;
    const buttons = ready
      ? `<button class="btn btn-dark accept-btn">Accept</button>
         <button class="btn btn-outline-dark decline-btn">Decline</button>`
      : `<button class="btn btn-outline-dark cancel-btn">Cancel hold</button>`;
    col.innerHTML = `<article class="book-card">
        <h3>${safeText(hold.title)}</h3>
        ${details}
        <div class="card-bottom">
          <a class="btn btn-outline-dark details-btn" href="literature.html?id=${encodeURIComponent(hold.literature_id)}">View details</a>
          ${buttons}
        </div>
      </article>`;
    if (ready) {
      col.querySelector('.accept-btn').onclick = () => answerHold(hold, 'accept');
      col.querySelector('.decline-btn').onclick = () => answerHold(hold, 'decline');
    } else {
      col.querySelector('.cancel-btn').onclick = () => answerHold(hold, 'cancel');
    }
    holdList.appendChild(col);
  }
}

async function loadHolds() {
  try {
    const data = await libraryRequest('holds');
    holds = data.holds;
    drawHolds();
  } catch (error) {
    showPageError(error);
  }
}

async function answerHold(hold, action) {
  const questions = {
    accept: `Borrow ${hold.title} now?`,
    decline: `Decline ${hold.title}? It will go to the next person in line.`,
    cancel: `Cancel your hold on ${hold.title}?`,
  };
  if (!confirm(questions[action])) return;
  try {
    const result = await libraryRequest(`holds/${hold.hold_id}/${action}`, { method: 'POST' });
    showPageMessage(result.message);
  } catch (error) {
    showPageError(error);
  }
  await loadHolds();
}

// When an offer's time runs out, ask the server again so it moves to the next person
function checkDeadlines() {
  const expired = holds.some(hold => hold.status === 'READY' && utcMillis(hold.decision_deadline) <= Date.now());
  if (expired) loadHolds();
  else drawHolds();
}

document.addEventListener('visibilitychange', () => { if (!document.hidden) loadHolds(); });

(async () => {
  try {
    await checkLogin();
    document.querySelector('#private-content').hidden = false;
    await loadHolds();
    setInterval(() => { if (!document.hidden) loadHolds(); }, 15000);  // queue positions stay up to date
    setInterval(() => { if (!document.hidden) checkDeadlines(); }, 30000);  // countdown
  } catch (error) {
    showPageError(error);
  }
})();
