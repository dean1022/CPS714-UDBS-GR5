# Testing instructions

## Render settings for demos and testing

Set these on Render under Dashboard → cps714-udbs-gr5 → Environment, then save and redeploy. Leave a setting empty or delete it to use the normal rule.

| Setting | What it does | Normal rule |
| --- | --- | --- |
| `UDBS_DEMO_LOAN_MINUTES` | Makes new loans last this many minutes | 14 days (BR-01) |
| `UDBS_DEMO_HOLD_MINUTES` | Gives new hold offers this many minutes to accept or decline | 72 hours (BR-08) |
| `UDBS_MAX_ACTIVE_LOANS` | Lowers how many loans one user can have | 30 (BR-02) |
| `UDBS_MAX_CONCURRENT_LOANS` | Lowers how many access slots each book has | 15 (BR-03) |

- The two demo settings take whole minutes from 1 to 525600. Any other value makes borrowing or offering a hold fail with an error until it's fixed.
- Changes only apply to new loans and new offers, so borrow or free up a new slot after redeploying.
- Example for a quick demo: `UDBS_DEMO_LOAN_MINUTES=3`, `UDBS_DEMO_HOLD_MINUTES=3` and `UDBS_MAX_CONCURRENT_LOANS=1`, so one borrow fills a book and holds can be shown right away.
- Remove all four settings before the final presentation so the site follows the business rules.

## Automated tests

`backend/test_udbs.py` checks the backend rules for Sprints 1 to 3.

1. Install pytest: `pip install pytest`
2. Set `TEST_DATABASE_URL` to a Postgres connection string. A separate test database or a local Postgres is safest.
3. From the `backend` folder, run: `pytest test_udbs.py -v`

Each test makes its own `udbs_test` schema and deletes it afterwards, so the normal tables aren't touched. Without `TEST_DATABASE_URL`, the tests are skipped.

## Checks to do in the browser

These happen on the website, so the automated tests can't cover them.

- Catalogue sorts by title and by author.
- A full book shows the current hold queue and "Place a hold". After placing it, the button shows your place in line.
- The Holds page shows each hold's position (for example "#2 of 3"), and positions move up when someone ahead cancels.
- A ready hold shows a countdown with Accept and Decline. Accepting adds the book to the Personal Library.
- When a ready hold's time runs out, it disappears from that user's Holds page and the next person gets the offer.
- The Personal Library shows the time left on each loan, and Renew explains why when it's blocked.
- Personal Info lets you change your preferred name and pronouns, and the new name shows after logging in again. The legal name, university ID, email and status can't be edited.
- Pages and the footer look right on a laptop and on a phone.
