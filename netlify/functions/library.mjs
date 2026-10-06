import { readFileSync } from "node:fs";
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { getStore } from "@netlify/blobs";

// Same demo accounts and books from the merged database, saved as JSON for Netlify.
const users = JSON.parse(readFileSync("data/users.json", "utf8"));
const books = JSON.parse(readFileSync("data/books.json", "utf8"));
const sessionHours = 8;

function reply(data, status = 200, cookie = "") {
  let headers = {
    "Content-Type": "application/json",
    "Cache-Control": "no-store"
  };
  if (cookie) headers["Set-Cookie"] = cookie;
  return new Response(JSON.stringify(data), { status, headers });
}

function getToken(request) {
  let cookies = (request.headers.get("cookie") || "").split(";");
  for (let cookie of cookies) {
    let parts = cookie.trim().split("=");
    if (parts[0] === "udbs_session" && /^[a-f0-9]{64}$/.test(parts[1])) {
      return parts[1];
    }
  }
  return "";
}

function sessionCookie(token, request, age) {
  // HttpOnly means the page's JavaScript can't read the login cookie.
  let cookie = `udbs_session=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${age}`;
  if (new URL(request.url).protocol === "https:") cookie += "; Secure";
  return cookie;
}

function userInfo(user) {
  return { university_id: user.university_id, display_name: user.display_name, status: user.status };
}

function passwordMatches(password, savedPassword) {
  // This follows auth.py so we can keep Megan's existing demo passwords.
  let parts = savedPassword.split("$");
  let enteredHash = createHash("sha256").update(parts[0] + password).digest("hex");
  let savedHash = parts[1];
  return savedHash.length === enteredHash.length &&
    timingSafeEqual(Buffer.from(savedHash), Buffer.from(enteredHash));
}

export default async function library(request) {
  const url = new URL(request.url);
  const action = url.searchParams.get("action") || "session";
  const method = request.method;

  if (!["login", "logout", "session", "books", "book"].includes(action)) {
    return reply({ message: "That page wasn't found." }, 404);
  }
  let expectedMethod = action === "login" || action === "logout" ? "POST" : "GET";
  if (method !== expectedMethod) return reply({ message: "This request method isn't supported." }, 405);

  if (method === "POST") {
    let origin = request.headers.get("origin");
    if (origin && origin !== url.origin) return reply({ message: "Please use the library website to sign in." }, 403);
    if (!(request.headers.get("content-type") || "").includes("application/json")) {
      return reply({ message: "Please send JSON." }, 415);
    }
  }

  try {
    // Netlify stores sessions here, rather than in a JavaScript variable that resets.
    // Strong reads make a deleted session stop working right after logout.
    const sessions = getStore({ name: "udbs-sessions", consistency: "strong" });
    const token = getToken(request);

    if (action === "login") {
      let input;
      try { input = await request.json(); }
      catch { return reply({ message: "Couldn't read the login details." }, 400); }
      if (!input || typeof input.identifier !== "string" || typeof input.password !== "string") {
        return reply({ message: "Enter your university ID or email and password." }, 400);
      }
      let identifier = input.identifier.trim().toLowerCase();
      if (!identifier || !input.password || identifier.length > 200 || input.password.length > 200) {
        return reply({ message: "Enter your university ID or email and password (under 200 characters)." }, 400);
      }
      let user = users.find(function (person) {
        return person.university_id === identifier || person.email.toLowerCase() === identifier;
      });
      if (!user || !passwordMatches(input.password, user.password_hash)) {
        return reply({ message: "That ID/email or password doesn't match. Please try again." }, 401);
      }
      if (token) await sessions.delete(token);
      let newToken = randomBytes(32).toString("hex");
      await sessions.setJSON(newToken, {
        university_id: user.university_id,
        expires: Date.now() + sessionHours * 60 * 60 * 1000
      });
      return reply({ user: userInfo(user) }, 200, sessionCookie(newToken, request, sessionHours * 3600));
    }

    if (action === "logout") {
      if (token) await sessions.delete(token);
      return reply({ message: "You're logged out." }, 200, sessionCookie("", request, 0));
    }

    let session = token ? await sessions.get(token, { type: "json" }) : null;
    if (!session || session.expires <= Date.now()) {
      if (session) await sessions.delete(token);
      return reply({ message: "Please sign in again. Your session has ended." }, 401, sessionCookie("", request, 0));
    }
    let user = users.find(person => person.university_id === session.university_id);
    if (!user) return reply({ message: "This university account wasn't found." }, 401);
    if (action === "session") return reply({ user: userInfo(user) });

    if (action === "book") {
      let id = Number(url.searchParams.get("id"));
      let book = books.find(book => book.literature_id === id);
      if (!book) return reply({ message: "We couldn't find that literature item." }, 404);
      return reply({ book });
    }

    // Sprint 1: just browsing and searching. Borrowing comes later.
    let search = (url.searchParams.get("q") || "").trim().toLowerCase();
    let category = url.searchParams.get("category") || "";
    let sort = url.searchParams.get("sort") || "title";
    let results = books.filter(function (book) {
      let words = [book.title, book.authors.join(" "), book.category, book.keywords.join(" ")].join(" ");
      return words.toLowerCase().includes(search) && (!category || book.category === category);
    });
    results.sort(function (a, b) {
      if (sort === "author") return a.authors.join(", ").localeCompare(b.authors.join(", ")) || a.title.localeCompare(b.title);
      return a.title.localeCompare(b.title);
    });
    let categories = [...new Set(books.map(book => book.category))].sort();
    return reply({ books: results, categories, total: books.length });
  } catch (error) {
    console.error("Library request failed:", error.message);
    return reply({ message: "The library couldn't load right now. Please try again." }, 503);
  }
}
