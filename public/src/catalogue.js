let searchInput = document.querySelector("#search");
let categorySelect = document.querySelector("#category");
let sortSelect = document.querySelector("#sort");
let bookList = document.querySelector("#book-list");
let lastSearch = 0;

function getFilters() {
  let filters = new URLSearchParams();
  if (searchInput.value.trim()) filters.set("q", searchInput.value.trim());
  if (categorySelect.value) filters.set("category", categorySelect.value);
  filters.set("sort", sortSelect.value);
  return filters;
}

async function loadBooks(filters) {
  let searchNumber = ++lastSearch;
  document.querySelector("#page-message").textContent = "";
  document.querySelector("#result-count").textContent = "Loading titles...";
  document.querySelector("#empty-message").hidden = true;
  bookList.innerHTML = "";
  try {
    let data = await libraryRequest("books&" + filters.toString());
    // Ignore an older response if another search has already been sent.
    if (searchNumber !== lastSearch) return;
    categorySelect.innerHTML = '<option value="">All categories</option>';
    data.categories.forEach(function (category) {
      let option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      categorySelect.appendChild(option);
    });
    let selectedCategory = filters.get("category") || "";
    // Keep a stale category visible so an old bookmarked filter can still be cleared.
    if (selectedCategory && !data.categories.includes(selectedCategory)) {
      let option = document.createElement("option");
      option.value = selectedCategory;
      option.textContent = selectedCategory;
      categorySelect.appendChild(option);
    }
    categorySelect.value = selectedCategory;
    document.querySelector("#result-count").textContent =
      `${data.books.length} of ${data.total} titles`;
    document.querySelector("#empty-message").hidden = data.books.length !== 0;
    data.books.forEach(function (book) {
      let column = document.createElement("div");
      column.className = "col-md-6 col-lg-4";
      let available = book.available_slots > 0;
      let slots = available
        ? `${book.available_slots} / ${book.total_access_slots} slots available`
        : "No access slots available";
      let link =
        "literature.html?id=" + book.literature_id + "&" + filters.toString();
      column.innerHTML = `
        <article class="book-card">
          <span class="category-label">${safeText(book.category)}</span>
          <h3>${safeText(book.title)}</h3>
          <p class="author">${safeText(book.authors.join(", ") || "Author not listed")}</p>
          <div class="card-bottom"><span class="slots ${available ? "" : "unavailable"}">${slots}</span><a class="details-link">View details &rarr;</a></div>
        </article>`;
      column.querySelector(".details-link").href = link;
      column
        .querySelector(".details-link")
        .setAttribute("aria-label", "View details for " + book.title);
      bookList.appendChild(column);
    });
  } catch (error) {
    if (searchNumber !== lastSearch) return;
    document.querySelector("#result-count").textContent = "";
    showPageError(error);
  }
}

function searchBooks(event) {
  if (event) event.preventDefault();
  let filters = getFilters();
  // URL filters mean the Back link doesn't forget what we searched for.
  window.history.replaceState(null, "", "catalogue.html?" + filters.toString());
  loadBooks(filters);
}

function clearFilters() {
  searchInput.value = "";
  categorySelect.value = "";
  sortSelect.value = "title";
  searchBooks();
  searchInput.focus();
}

async function startCatalogue() {
  try {
    let user = await checkLogin();
    document.querySelector("#user-name").textContent = user.display_name;
    document.querySelector("#user-status").textContent =
      user.status + " · " + user.university_id;
    document.querySelector("#private-content").hidden = false;
    let filters = new URLSearchParams(window.location.search);
    searchInput.value = filters.get("q") || "";
    sortSelect.value = filters.get("sort") === "author" ? "author" : "title";
    await loadBooks(filters);
  } catch (error) {
    showPageError(error);
  }
}

document.querySelector("#search-form").addEventListener("submit", searchBooks);
categorySelect.addEventListener("change", searchBooks);
sortSelect.addEventListener("change", searchBooks);
document.querySelector("#clear-button").addEventListener("click", clearFilters);
startCatalogue();
