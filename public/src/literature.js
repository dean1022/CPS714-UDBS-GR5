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
    if (book.available_slots > 0) {
      availability.textContent = `Available · ${book.available_slots} of ${book.total_access_slots} access slots`;
    } else {
      availability.textContent = "Currently unavailable · No access slots open";
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
    const myLoans = await libraryRequest('loans');
    const borrowed = myLoans.loans.some(loan => Number(loan.literature_id) === Number(book.literature_id));
    borrowBtn.disabled = borrowed || book.available_slots <= 0;
    borrowBtn.textContent = borrowed ? 'Borrowed' : book.available_slots <= 0 ? 'No slots available' : 'Borrow this book';
    borrowBtn.onclick = async () => {
      borrowBtn.disabled = true;
      document.querySelector('#borrow-message').textContent = '';
      try {
        await libraryRequest('borrow/' + book.literature_id, { method: 'POST' });
        flashBorrowSuccess();
        // No reload, redirect or progress message. Only the button and availability change.
        borrowBtn.textContent = 'Borrowed';
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
        borrowBtn.disabled = false;
      }
    };
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
showLiterature();
