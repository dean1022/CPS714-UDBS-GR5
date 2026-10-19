let loginForm = document.querySelector("#login-form");
let passwordInput = document.querySelector("#password");
let loginMessage = document.querySelector("#login-message");
let params = new URLSearchParams(window.location.search);
if (params.has("logout")) loginMessage.textContent = "You're logged out. See you next time!";
if (params.has("expired")) loginMessage.textContent = "Please sign in again. Your session has ended.";

document.querySelector("#show-password").addEventListener("change", function (event) {
  passwordInput.type = event.target.checked ? "text" : "password";
});

async function signIn(event) {
  event.preventDefault();
  let button = document.querySelector("#login-button");
  button.disabled = true;
  button.textContent = "Signing in...";
  loginMessage.textContent = "";
  try {
    await libraryRequest("login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        identifier: document.querySelector("#identifier").value.trim(),
        password: passwordInput.value
      })
    });
    passwordInput.value = "";
    window.location.replace("catalogue.html");
  } catch (error) {
    loginMessage.textContent = error.message;
    passwordInput.value = "";
    passwordInput.focus();
    button.disabled = false;
    button.textContent = "Sign in →";
  }
}
loginForm.addEventListener("submit", signIn);
