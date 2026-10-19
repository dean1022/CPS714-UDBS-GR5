// Browser-only UI logic. All business rules and database operations happen on Render (Python).
const API_URL = "__RENDER_API_URL__"; // set this URL in public/src/common.js after deploying Render
const libraryUrl = API_URL.replace(/\/$/, "") + "/api";
async function libraryRequest(action, options={}) {
  const parts = action.split("&");
  const search = new URLSearchParams(parts.slice(1).join("&"));
  let endpoint = parts[0] === "session" ? "/session" : parts[0] === "books" ? "/books?"+search : parts[0] === "book" ? "/book/"+encodeURIComponent(search.get("id")) : "/"+parts[0];
  let token = sessionStorage.getItem("udbs_token");
  let headers={...(options.headers||{})};
  if(token) headers.Authorization="Bearer "+token;
  let response;
  try { response=await fetch(libraryUrl+endpoint,{...options,headers,cache:"no-store"}); }
  catch { throw new Error("Cannot connect to the Python backend on Render. Check API_URL and CORS."); }
  const ct=response.headers.get("content-type")||"";
  let data=ct.includes("application/json")?await response.json():{};
  if(response.status===401&&parts[0]!=="login"){
    sessionStorage.removeItem("udbs_token");
    location.replace("index.html?expired=1");throw new Error("Please sign in again.");
  }
  if(!response.ok) throw new Error(data.message||data.detail||"Request failed");
  if(parts[0]==="login")sessionStorage.setItem("udbs_token",data.token);
  return data;
}
function showPageError(err) {let node=document.querySelector("#page-message");if(node){node.textContent=err.message||"Request failed";node.classList.add("error");}}
async function checkLogin(){const d=await libraryRequest("session");const b=document.querySelector("#logout-button");if(b)b.hidden=false;return d.user;}
async function logout(){try{await libraryRequest("logout",{method:"POST"});}catch(e){console.warn(e.message);}sessionStorage.removeItem("udbs_token");location.replace("index.html?logout=1");}
function safeText(s){let e=document.createElement("span");e.textContent=s??"";return e.innerHTML;}
const logoutButton=document.querySelector("#logout-button");if(logoutButton) logoutButton.addEventListener("click",logout);
