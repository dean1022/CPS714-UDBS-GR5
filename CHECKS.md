# Sprint 1 checks

## Earlier local server checks

Before removing Netlify Dev, the API test script passed all 19 checks against the real local Netlify function and its local Blobs store:

- Catalogue requires login
- Wrong password is rejected
- Student login succeeds
- Login cookie is HttpOnly
- Responses do not expose password hashes
- All five titles are returned
- Seeded availability is 15 slots per title
- Keyword search (`sql`)
- Author search (`Stephen`)
- Category search (`Physics`)
- Title search (`Sapiens`)
- Category filter with author sorting
- Combined filters with no results
- Literature details
- Unknown literature ID
- A logged-out cookie cannot be reused
- Faculty email login, including uppercase email
- The private user-data file is not served as a static page
- Cross-site login requests are rejected

JavaScript syntax checks also passed. The local server used Node 24.19.0 and Netlify CLI 27.11.2.

## Browser checks

Checked in Chromium at a 1280px desktop width:

- Invalid password message and cleared password field
- Student login and five catalogue cards
- Search, details and back navigation with the search retained
- Empty results and clear filters
- Category filtering and author sorting
- Missing-item error and logout
- Direct catalogue access after logout returns to login

At a 390px phone width, faculty login and catalogue navigation worked. Login and catalogue had no horizontal overflow. A small overflow on the details page was fixed by removing the extra Bootstrap row gutters on mobile. The changed details layout was then checked separately using the same book data and a mocked session/API response. It had no horizontal overflow. The fix only changed CSS.

Screenshots are in `screenshots`. The mobile-details screenshot comes from the isolated layout check; the other screenshots used the real local function.

These are local checks. The project has not been deployed to the user's Netlify account, and production hosting has not been verified.

## GitHub deployment version

The Netlify CLI dependency, local start command and local dev configuration have been removed. The hosted function and its deployment settings are still included.

`npm test` checks how the browser request helper handles valid JSON, rejected credentials, expired sessions, a missing function and invalid server responses. `npm run build` checks the function's JavaScript syntax. These checks do not deploy the app.

After deploying, you can run the existing 19 API checks against your own site with Node.js 22 or newer:

```sh
npm run test:site -- https://your-project.netlify.app
```

Replace that example with your site's address. This test signs in and out using the demo accounts. The hosted version has not been tested yet.
