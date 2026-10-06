# University Digital Borrowing System

Welcome to UDBS, our CPS714 Group 5 project. This is the Sprint 1 version of the app. You can sign in, browse the electronic literature catalogue and check the information for each title.

For now, the app uses sample accounts and literature records. Borrowing, reading, returns, renewals and holds will be added in later sprints.

## Getting started

If you've been given a link to the app, open it in your browser. You don't need to install anything to use the hosted version.

To put your own copy online, upload the contents of the extracted `udbs_sprint1` folder to a GitHub repository. `package.json`, `netlify.toml`, `public`, `data` and `netlify` should all be at the top level of the repository. Upload the actual files and folders, not the ZIP.

In Netlify, select **Add new project**, then **Import an existing project**. Choose GitHub and select your repository. Use these settings:

| Setting             | Value               |
| ------------------- | ------------------- |
| Base directory      | Leave blank         |
| Build command       | `npm run build`     |
| Publish directory   | `public`            |
| Functions directory | `netlify/functions` |

These settings are also saved in `netlify.toml`. Netlify installs the dependencies and deploys the login service along with the pages. You don't need to install Netlify Dev or run a local server.

Once the deployment finishes, open the site's Netlify address and sign in using one of the accounts below. You can use the provided `netlify.app` address without buying a domain. Later changes pushed to the connected GitHub branch will trigger another deployment.

Keep the `netlify` and `data` folders in the repository. The login and catalogue need the hosted function, so uploading only `public` won't give you a working app. Open the deployed Netlify site to use the app. Opening an HTML file on your computer only shows the page layout.

Netlify's [repository deployment guide](https://docs.netlify.com/start/quickstarts/deploy-from-repository/) has more help with connecting GitHub.

## Signing in

Use one of these accounts to try the app:

| Account | University ID | Password       |
| ------- | ------------- | -------------- |
| Student | `501000001`   | `Library2026!` |
| Faculty | `700000001`   | `Library2026!` |

You can also sign in with `ava.chen@torontomu.ca` for the student account or `elaine.whitfield@torontomu.ca` for the faculty account.

Enter the ID or email and password, then select **Sign in**. If you want to check what you've typed, select **Show password**.

These are demo accounts. The app isn't connected to the university's login system, so please don't enter your real university password. There isn't an account registration option in this version.

## Finding a title

Once you're signed in, you'll see the catalogue. Each card shows the title, author, publication year, category and available access slots.

To find something specific:

1. Enter a title, author, category or keyword in the search box.
2. Select **Search** or press Enter.
3. Use the **Category** dropdown if you want to narrow the results.
4. Use **Sort by** to put the results in alphabetical order by title or author.

For a quick example, try searching for `sql`. You should see _Database System Concepts_.

You can combine a search with a category filter. If nothing matches, try a different search or select **Clear filters** to see the full catalogue again.

## Viewing literature information

Select **View details** on a title's card to open its information page. You'll find its authors, publication year, category, keywords and available access slots there. Some titles don't have a summary yet, so the page will let you know when one isn't available.

Select **Back to catalogue** to return to your results. Your search and filters will still be there. The **Catalogue** link in the navigation bar opens the full catalogue.

The access-slot counts are sample data for Sprint 1. They don't change through borrowing yet because that feature isn't available in this version.

## Logging out

Select **Log out** in the top-right corner when you're finished. You'll return to the sign-in page and will need to sign in again to access the catalogue.

Login sessions last up to eight hours. If your session ends while you're using the app, you'll be asked to sign in again.

## If something isn't working

- **Your login isn't accepted:** Check that you're using one of the demo accounts above and that the password matches, including the capital letters and exclamation mark.
- **The catalogue has no results:** Clear your filters and try searching again.
- **A title can't be found:** Go back to the catalogue and open it from its card.
- **The login and catalogue service is unavailable:** Check that the latest Netlify deployment succeeded and includes the `library` function. Confirm that the repository contains `netlify/functions/library.mjs` and that the deployment settings match the table above.
- **You see a connection error:** Check your internet connection, refresh the page and try again. If it keeps happening, check the function logs in Netlify for the error.

## About this version

UDBS is a course prototype for students and faculty. The interface uses HTML, CSS, JavaScript and Bootstrap. The login service uses Node.js, Netlify Functions and Netlify Blobs. Bootstrap's licence is included in the project files.
