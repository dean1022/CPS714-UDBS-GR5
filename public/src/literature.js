async function showLiterature() {
  try {
    await checkLogin();
    let params = new URLSearchParams(window.location.search);
    let data = await libraryRequest(
      "book&id=" + encodeURIComponent(params.get("id") || ""),
    );
    let book = data.book;
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
    document.querySelector("#book-summary").textContent =
      book.summary ||
      "There isn't a summary for this title in the catalogue yet.";
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
