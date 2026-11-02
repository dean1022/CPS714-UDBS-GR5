// Render cached book information immediately so the details page doesn't sit blank
// while the network requests complete. The API remains the source of truth.
function renderBook(book) {
  document.title = book.title + " | UDBS";
    document.querySelector("#book-title").textContent = book.title;
    document.querySelector("#cover-title").textContent = book.title;
    document.querySelector("#book-author").textContent =
      "By " + ((book.authors || []).join(", ") || "Author not listed");
    document.querySelector("#book-category").textContent = book.category;
    document.querySelector("#cover-category").textContent = book.category;
    document.querySelector("#book-subject").textContent = book.category;
    document.querySelector("#book-year").textContent =
      book.publication_year || "Not listed";
    document.querySelector("#book-keywords").textContent =
      (book.keywords || []).join(", ") || "Not listed";
    let summary = book.summary;

    //Putting a blank line between paragraphs
    if (Array.isArray(summary)) {
      summary = summary.join("\n\n");
    }

    document.querySelector("#book-summary").textContent =
      summary || "There isn't a summary for this title in the catalogue yet.";
    let availability = document.querySelector("#availability");
    const waiting = Number(book.people_waiting || 0);
    const waitingText = waiting ? ` · ${waiting} waiting in the hold queue` : "";
    if (book.available_slots > 0 && waiting === 0) {
      availability.textContent = `Available · ${book.available_slots} of ${book.total_access_slots} access slots`;
      availability.classList.remove("unavailable");
    } else {
      availability.textContent = "Currently unavailable · No access slots open" + waitingText;
      availability.classList.add("unavailable");
    }
  document.querySelector('#private-content').hidden = false;
}

function flashBorrowSuccess() {
  document.body.classList.remove('borrow-flash');
  void document.body.offsetWidth;
  document.body.classList.add('borrow-flash');
  setTimeout(() => document.body.classList.remove('borrow-flash'), 320);
}

async function showLiterature() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get('id') || '';
  const borrowBtn = document.querySelector('#borrow-book');
  borrowBtn.disabled = true;
  let cached = null;
  try {
    cached = JSON.parse(sessionStorage.getItem('udbs_selected_book') || 'null');
  } catch (_) {}
  if (cached && String(cached.literature_id) === String(id)) {
    renderBook(cached);
  }
  try {
    await checkLogin();
    const data = await libraryRequest('book&id=' + encodeURIComponent(id));
    const book = data.book;
    renderBook(book);
    await setupBookAction(book);
    params.delete('id');
    document.querySelector('#back-link').href = 'catalogue.html?' + params.toString();
    document.querySelector('#page-message').textContent = '';
  } catch (error) {
    // An error is the only reason to display a page-level message.
    document.querySelector('#private-content').hidden = true;
    showPageError(error);
    const back = document.createElement('a');
    back.href = 'catalogue.html';
    back.textContent = ' Back to catalogue';
    document.querySelector('#page-message').appendChild(back);
  }
}
// Decides what the main button does: borrow, place a hold (US-10), or show the user's hold
async function setupBookAction(book) {
  const button = document.querySelector('#borrow-book');
  const message = document.querySelector('#borrow-message');
  const queueBox = document.querySelector('#hold-queue');
  const [loanData, holdData] = await Promise.all([libraryRequest('loans'), libraryRequest('holds')]);
  const borrowed = loanData.loans.some(loan => Number(loan.literature_id) === Number(book.literature_id));
  const myHold = holdData.holds.find(hold => Number(hold.literature_id) === Number(book.literature_id));
  const canBorrow = book.available_slots > 0 && Number(book.people_waiting || 0) === 0;
  queueBox.hidden = true;
  button.onclick = null;

  if (borrowed) {
    button.disabled = true;
    button.textContent = 'Borrowed';
    return;
  }

  if (myHold) {
    button.disabled = true;
    if (myHold.status === 'READY') {
      button.textContent = 'Ready for you';
      message.innerHTML = 'A slot is saved for you. <a href="holds.html">Accept or decline it on your Holds page</a>.';
    } else {
      button.textContent = `On hold · #${myHold.queue_position} in line`;
      message.innerHTML = '<a href="holds.html">See your holds</a>';
    }
    return;
  }

  if (canBorrow) {
    button.disabled = false;
    button.textContent = 'Borrow this book';
    button.onclick = () => borrowBook(book);
    return;
  }

  // No free slot: show the current queue first, then let them place a hold
  const queueData = await libraryRequest('book/' + encodeURIComponent(book.literature_id) + '/queue');
  showQueue(queueData.queue);
  button.disabled = false;
  button.textContent = 'Place a hold';
  button.onclick = async () => {
    button.disabled = true;
    message.textContent = '';
    try {
      await libraryRequest('hold/' + book.literature_id, { method: 'POST' });
      const updated = await libraryRequest('book&id=' + encodeURIComponent(book.literature_id));
      renderBook(updated.book);
      await setupBookAction(updated.book);
    } catch (error) {
      message.textContent = error.message;
      button.disabled = false;
    }
  };
}

// The current line for this book, without other users' names
function showQueue(queue) {
  const queueBox = document.querySelector('#hold-queue');
  let html = `<p class="hold-queue-title">${queue.length ? queue.length + ' in the hold queue' : 'Nobody is in the hold queue yet'}</p>`;
  if (queue.length) {
    html += '<ol class="hold-queue-list">' + queue.map(spot =>
      `<li>#${safeText(spot.position)} · placed ${safeText(torontoTime(spot.placed_at))}</li>`).join('') + '</ol>';
  }
  html += `<p class="hold-queue-note">If you place a hold, you'll be #${queue.length + 1} in line.</p>`;
  queueBox.innerHTML = html;
  queueBox.hidden = false;
}

async function borrowBook(book) {
  const button = document.querySelector('#borrow-book');
  button.disabled = true;
  document.querySelector('#borrow-message').textContent = '';
  try {
    await libraryRequest('borrow/' + book.literature_id, { method: 'POST' });
    flashBorrowSuccess();
    // No reload, redirect or progress message. Only the button and availability change.
    button.textContent = 'Borrowed';
    book.available_slots = Math.max(0, Number(book.available_slots) - 1);
    renderBook(book);
    try {
      const updated = await libraryRequest('book&id=' + encodeURIComponent(book.literature_id));
      renderBook(updated.book);
    } catch (e) {
      console.warn('Availability refresh failed after successful borrowing:', e);
    }
  } catch (error) {
    document.querySelector('#borrow-message').textContent = error.message;
    button.disabled = false;
  }
}

showLiterature();
