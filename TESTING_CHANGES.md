# Sprint 2 testing and deployment notes

Only the files included in this patch need replacing. Preserve your current working public/src/common.js and the About Us page.

## PDFs
The five PDFs in backend/ebooks are **demonstration placeholders**, not the full published books. The backend requires an active loan and a Bearer token to serve each PDF. For real content, replace each PDF with a legally supplied PDF using the same filename (the current database file_url references the corresponding .txt). Do not publish unrestricted copies in public/.

## Loan duration test mode
By default, UDBS_DEMO_LOAN_MINUTES is unset and original 14-day borrowing applies. To run a temporary short-loan test, set Render environment variable UDBS_DEMO_LOAN_MINUTES=3 and redeploy. Borrow a **new** book with a test account. Existing loans stay unchanged. Wait 3-4 minutes, then refresh the Personal Library. Expired loans are checked whenever the API runs. To test unattended returns, configure an authenticated scheduler calling POST /api/jobs/expire with Authorization: Bearer <CRON_SECRET>; merely shortening the loan duration does not schedule automatic jobs.

When finished, REMOVE UDBS_DEMO_LOAN_MINUTES from Render and redeploy to restore 14-day loans. The loan timestamp format is minute-granularity, so a 3-minute loan may appear to end somewhat earlier than 180 seconds after you click Borrow.

## Netlify -> Render GUI check
Open https://udbs.netlify.app and press F12 -> Network -> Fetch/XHR. Sign in and browse the catalogue. Look for a request to https://cps714-udbs-gr5.onrender.com/api/books or /api/session returning HTTP 200. Select it to inspect Request URL, response status and response Preview. HTTP 200 with book data establishes the browser made a successful request to Render. /api/health from a separate tab checks Render alone, not the connection from Netlify. A 401 means authentication was not sent or the session expired. A CORS error means the frontend origin or Render CORS settings need checking. Do not share Authorization header values, passwords or session tokens.

## Additional acceptance tests
- Borrowed card links to `literature.html?id=<literature_id>` and shows the matching catalogue details.
- Read PDF works only while the loan is active.
- After an early return or expiration, the backend rejects direct /api/read/{book_id} calls.
- Multiple loans have independent due dates; refresh does not reset them.
- Test 15 concurrent loans with multiple users only in a dedicated test dataset. The 30-user-loan cap cannot be demonstrated with only 5 titles without adding test titles.

## Deploy
Commit backend/api.py, backend/library.py and backend/ebooks/*.pdf to the branch used by Render, then redeploy Render. Commit public/personal-library.html, public/src/personal-library.js and public/src/styles.css to the branch used by Netlify, then redeploy Netlify. Other working files remain unchanged.
