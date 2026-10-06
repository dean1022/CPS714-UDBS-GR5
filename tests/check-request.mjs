import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

// Try the page's request helper with the responses a server might send.
let reply;
let redirectedTo = "";
let content = { hidden: false };
const page = vm.createContext({
  fetch: async () => reply,
  document: { querySelector: selector => selector === "#private-content" ? content : null },
  window: { location: { replace: url => { redirectedTo = url; } } }
});
vm.runInContext(readFileSync("public/src/common.js", "utf8"), page);

reply = Response.json({ user: { status: "student" } });
assert.equal((await page.libraryRequest("login")).user.status, "student");

reply = Response.json({ message: "Wrong password." }, { status: 401 });
await assert.rejects(page.libraryRequest("login"), /Wrong password/);
assert.equal(redirectedTo, "");

reply = new Response("Function not found...", { status: 404 });
await assert.rejects(page.libraryRequest("login"), /deployment includes the library function/);

reply = new Response("<html>Service unavailable</html>", { status: 502 });
await assert.rejects(page.libraryRequest("login"), /didn't respond properly/);

reply = new Response("broken JSON", { headers: { "Content-Type": "application/json" } });
await assert.rejects(page.libraryRequest("login"), /unreadable response/);

reply = Response.json({ message: "Session ended." }, { status: 401 });
await assert.rejects(page.libraryRequest("books"), /Please sign in again/);
assert.equal(redirectedTo, "index.html?expired=1");
assert.equal(content.hidden, true);
console.log("Passed all 6 request scenarios.");
