const libraryUrl = "/.netlify/functions/library";

async function libraryRequest(action, options = {}) {
  let response = await fetch(libraryUrl + "?action=" + action, options);
  // Netlify can send a plain error page if the function hasn't deployed.
  let contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    if (response.status === 404) {
      throw new Error("The login and catalogue service isn't available. Check that the Netlify deployment includes the library function.");
    }
    throw new Error("The library service didn't respond properly. Please try again shortly.");
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("The library service sent an unreadable response. Please try again shortly.");
  }
  if (response.status === 401 && action !== "login") {
    let content = document.querySelector("#private-content");
    if (content) content.hidden = true;
    window.location.replace("index.html?expired=1");
    throw new Error("Please sign in again.");
  }
  if (!response.ok) throw new Error(data.message || "Something went wrong. Please try again.");
  return data;
}

function showPageError(error) {
  document.querySelector("#page-message").textContent = error.message || "Couldn't connect. Please try again.";
}

async function checkLogin() {
  let data = await libraryRequest("session");
  document.querySelector("#logout-button").hidden = false;
  return data.user;
}

async function logout() {
  let button = document.querySelector("#logout-button");
  button.disabled = true;
  try {
    await libraryRequest("logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    document.querySelector("#private-content").hidden = true;
    window.location.replace("index.html?logout=1");
  } catch (error) {
    showPageError(error);
    button.disabled = false;
  }
}

// Use textContent to escape catalogue text before putting it in a card.
function safeText(text) {
  let span = document.createElement("span");
  span.textContent = text;
  return span.innerHTML;
}

let logoutButton = document.querySelector("#logout-button");
if (logoutButton) {
  logoutButton.addEventListener("click", logout);
  // Recheck when coming back to a tab or an old browser-history page.
  window.addEventListener("pageshow", function (event) {
    if (event.persisted) window.location.reload();
  });
  window.addEventListener("pagehide", function () {
    document.querySelector("#private-content").hidden = true;
    logoutButton.hidden = true;
  });
  setInterval(function () {
    if (!document.hidden) checkLogin().catch(showPageError);
  }, 60000);
}
