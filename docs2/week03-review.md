# Week 3 — AI Code Review

Reviewed by: Claude (Opus 5.5, in Claude Code)    Date: 28 November 2026

Code reviewed: `bandfinder/` at commit `a7f8f86` (`app.py`, `db.py`, `schema/001_initial.sql`, templates).
Each "yes" below was checked by actually trying it against a temporary database, unless it says "by reading the code".

## Findings

| # | File:line | What it says is wrong | Is it real? | Action |
|---|---|---|---|---|
| 1 | app.py:176 | Usernames can contain `/`, which breaks that user's profile page | signed up as `a/b`, then `/user/a/b` gave 404 | Fix |
| 2 | app.py:176 | Usernames that differ only in capitals are both allowed, so someone could pretend to be another user | created both `Aoife` and `aoife` | Fix |
| 3 | app.py:396, db.py:37 | Mixes local time (`date.today()`) and UTC (`db.now()`), so expiry times and dates can be an hour out during Irish summer time | partly — by reading the code; only matters near midnight in summer | Fix |
| 4 | app.py:253 | Photos are checked by file extension only, not by what's inside the file | by reading the code; low risk because files are served as images | Fix |
| 5 | app.py:204 | No limit on wrong login attempts, so passwords can be guessed again and again | yes, by reading the code | Fix |
| 6 | app.py:561 | 'app.run(debug=True)' turns on the debugger, which can run code if the app is ever reachable from other computers | yes, by reading the code` | Not fix|

## What I fixed, and why
1. Users should not be able to use special characters in their usernames. This is common practice on many sign-up sites. 
2. Although this is something that the user should spot, I feel its better that their is no chance of this type of phishing happening on the site in the first place.
3. Claude wrote teh rule itself as python doesnt have an irish time: "I wrote the Irish summer-time rule myself instead of adding the tzdata library. If the EU ever changes the summer-time rule, irish_time.py would need updating." It is important that the time is the same for everyone using it. 99/100 only irish people living in Ireland will be using this site.
4. Better to be safe with this. The saved file will now get a .JPEG extension. 
5. A fixed limit is better for security reasons. 5 wrong passwords for one email within 15 minutes, that email can't log in, even with the right password. 5 is a fair amount of guesses.
## What I am knowingly leaving, and why
6. I dont want to remove this yet while I am still developing the site. This could be something I come back to at the end.

## What the reviewer got wrong
(reviewers hallucinate too. Did it invent a problem, or miss an obvious one?)

