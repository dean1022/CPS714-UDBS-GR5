# Sprint 2 testing

### Loan duration in minutes (`UDBS_DEMO_LOAN_MINUTES`)

The Render environment variable `UDBS_DEMO_LOAN_MINUTES` controls how long new loans last during testing. Enter an integer number of minutes, not days or hours. The updated `backend/library.py` converts that value into a readable duration using `format_loan_duration()`; the Personal Library calculates its live countdown using the saved expiry timestamp.

| Render value (minutes) | Readable duration     |
| ---------------------: | --------------------- |
|                    `3` | 3 minutes             |
|                   `30` | 30 minutes            |
|                   `60` | 1 hour                |
|                   `90` | 1 hour 30 minutes     |
|                 `1440` | 1 day                 |
|                 `1501` | 1 day 1 hour 1 minute |
|                `10080` | 7 days                |
|                `20160` | 14 days               |

Env Variables Configuring on Render: Open Dashboard → cps714-udbs-gr5 → Environment, add or edit `UDBS_DEMO_LOAN_MINUTES`, enter your chosen integer and save/redeploy the web service. The allowed range is 1–525600 minutes (365 days). Invalid values will cause new borrowing attempts to fail with a configuration error.

Examples: Set `3` to test a loan expiring after three minutes. Set `20160` for exactly 14 days. Delete/unset `UDBS_DEMO_LOAN_MINUTES` to return to each book's configured loan period (normally 14 days). Changing this value does not edit existing loans, so borrow a new test book after redeploying. Because the frontend rounds down to whole minutes, immediately after borrowing a 3-minute loan it may display `2 minutes` even though only seconds have elapsed. The actual due time remains exactly three minutes after borrowing.

This setting is independent from `UDBS_MAX_ACTIVE_LOANS=3` and `UDBS_MAX_CONCURRENT_LOANS=3`. Restore the normal limits of 30 and 15 after limit testing. A shortened loan helps test expiry during API requests but does not prove unattended scheduled automatic returns; that requires a scheduled job.
