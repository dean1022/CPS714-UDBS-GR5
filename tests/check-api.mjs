// Run: npm run test:site -- https://your-project.netlify.app
// Only uses the demo accounts. This signs in and out of the chosen site.
import assert from "node:assert/strict";
const siteUrl = process.argv[2] || process.env.TEST_URL;
if (!siteUrl) {
  console.error("Add your deployed URL: npm run test:site -- https://your-project.netlify.app");
  process.exit(1);
}
const base = new URL(siteUrl).origin;
let cookie = "";
let passed = 0;
async function call(action, body, useCookie = cookie) {
  let options = { headers: { Cookie: useCookie } };
  if (body !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response = await fetch(base + "/.netlify/functions/library?action=" + action, options);
  let data = await response.json();
  return { response, data };
}
function check(condition, name) {
  assert.ok(condition, name);
  passed++;
  console.log("PASS: " + name);
}

let result = await call("books");
check(result.response.status === 401, "catalogue requires login");
result = await call("login", { identifier: "501000001", password: "wrong" });
check(result.response.status === 401, "wrong password rejected");
result = await call("login", { identifier: "501000001", password: "Library2026!" });
check(result.response.ok && result.data.user.status === "student", "student login");
cookie = result.response.headers.get("set-cookie").split(";")[0];
check(result.response.headers.get("set-cookie").includes("HttpOnly"), "login cookie is HttpOnly");
check(!JSON.stringify(result.data).includes("password_hash"), "password hash stays on server");
result = await call("books");
check(result.data.books.length === 5, "all five catalogue titles returned");
check(result.data.books.every(book => book.available_slots === 15), "Sprint 1 availability dataset");
for (let query of ["sql", "Stephen", "Physics", "Sapiens"]) {
  result = await call("books&q=" + query);
  check(result.data.books.length === 1, "search: " + query);
}
result = await call("books&category=Computer%20Science&sort=author");
check(result.data.books.length === 2 && result.data.books[0].authors[0] === "Abraham Silberschatz", "category and author sorting");
result = await call("books&q=Sapiens&category=Physics");
check(result.data.books.length === 0, "combined filters can return no results");
result = await call("book&id=1");
check(result.data.book.title === "Database System Concepts", "literature details");
result = await call("book&id=999");
check(result.response.status === 404, "missing literature item handled");
let oldCookie = cookie;
await call("logout", {});
result = await call("books", undefined, oldCookie);
check(result.response.status === 401, "logged-out cookie cannot be reused");
result = await call("login", { identifier: "ELAINE.WHITFIELD@TORONTOMU.CA", password: "Library2026!" });
check(result.response.ok && result.data.user.status === "faculty", "faculty email login is case-insensitive");
cookie = result.response.headers.get("set-cookie").split(";")[0];
await call("logout", {});
let response = await fetch(base + "/data/users.json");
check(response.status === 404, "private account file is not a static page");
response = await fetch(base + "/.netlify/functions/library?action=login", {
  method: "POST", headers: { "Content-Type": "application/json", Origin: "https://unrelated.example" }, body: "{}"
});
check(response.status === 403, "cross-site login rejected");
console.log(`${passed} API checks passed.`);
