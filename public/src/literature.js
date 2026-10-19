async function showLiterature() {
  try {
    await checkLogin();
    let params = new URLSearchParams(window.location.search);
    let data = await libraryRequest(
      "book&id=" + encodeURIComponent(params.get("id") || ""),
    );
    let book = data.book;
    let borrowBtn=document.querySelector('#borrow-book');
    // Compare active loans using the authenticated user's own library records.
    let myLoans=await libraryRequest('loans');
    const borrowed=myLoans.loans.some(loan=>Number(loan.literature_id)===Number(book.literature_id));
    borrowBtn.disabled=borrowed || book.available_slots<=0;
    borrowBtn.textContent=borrowed?'Borrowed':(book.available_slots<=0?'No slots available':'Borrow this book');
    borrowBtn.onclick=async()=>{
      borrowBtn.disabled=true;
      document.querySelector('#borrow-message').textContent='';
      try {
        await libraryRequest('borrow/'+book.literature_id,{method:'POST'});
        // Stay on this page. Show the new loan state without a progress message.
        borrowBtn.textContent='Borrowed';
        try {
          const updated=await libraryRequest('book&id='+encodeURIComponent(book.literature_id));
          const latest=updated.book;
          const availability=document.querySelector('#availability');
          if(latest.available_slots>0){
            availability.textContent=`Available · ${latest.available_slots} of ${latest.total_access_slots} access slots`;
            availability.classList.remove('unavailable');
          } else {
            availability.textContent='Currently unavailable · No access slots open';
            availability.classList.add('unavailable');
          }
        } catch(e) {
          // The loan succeeded; don't make the user think borrowing failed if the
          // optional availability refresh encounters a temporary network error.
          console.warn('Unable to refresh availability:',e);
        }
      } catch(err) {
        document.querySelector('#borrow-message').textContent=err.message;
        borrowBtn.disabled=false;
      }
    };

    document.title = book.title + " | UDBS";
    document.querySelector("#book-title").textContent = book.title;
    document.querySelector("#cover-title").textContent = book.title;
    document.querySelector("#book-author").textContent =
      "By " + (book.authors.join(", ") || "Author not listed");
    document.querySelector("#book-category").textContent = book.category;
    document.querySelector("#cover-category").textContent = book.category;
    document.querySelector("#book-subject").textContent = book.category;
    document.querySelector("#book-year").textContent =
      book.publication_year || "Not listed";
    document.querySelector("#book-keywords").textContent =
      book.keywords.join(", ") || "Not listed";
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
    params.delete("id");
    document.querySelector("#back-link").href =
      "catalogue.html?" + params.toString();
    document.querySelector("#page-message").textContent = "";
    document.querySelector("#private-content").hidden = false;
  } catch (error) {
    showPageError(error);
    let back = document.createElement("a");
    back.href = "catalogue.html";
    back.textContent = " Back to catalogue";
    document.querySelector("#page-message").appendChild(back);
  }
}
showLiterature();
