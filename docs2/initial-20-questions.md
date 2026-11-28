# Band Finder – Initial 20 Questions

At the start of the project, Claude asked 20 questions to plan the first version of Band Finder.
This file keeps only those questions and the answers given. Your answers are copied exactly as
you typed them. The full conversation is in `docs2/specification.md`.

## The prompt that started it

> I struggle to find new band mates or people to jam music with around Dublin/Ireland. I find that the current webpages like Boards.ie and Bandcamp are not very modern and are not very intuitive to use and navigate. I would like to create a webpage where a user could create a profile that could display small information about them, like what instrument they play, genres etc. A posting forum to narrow their search for band members with ways to filter and match their tastes.
>
> Could you please ask me 20 questions to help you create the initial web page.

---

## The basics

**1. Name:** What should the site be called? Is "BandFinder" a working title, or the final name?
> Band Finder

**2. Technology:** Should this use the same setup as your album club project (Python + Flask + SQLite, built-in `sqlite3`, `unittest` tests)? Or do you only want a static mock-up (HTML/CSS) for now?
> Python + Flask + SQLite with HTML CSS

**3. First version:** For this first webpage, do you want a working app with a database, or just the pages and layout so you can see the design?
> Create an initial database but I may change after.

## Who uses it

**4. Accounts:** Should people sign up with an email and password? Or should anyone be able to browse posts without an account, and only need one to post or message?
> Need and account. email and password. They can create a username for their profile.

**5. Age:** Is there a minimum age (for example 16+ or 18+)? This affects safety and privacy.
> 18+

## The profile

**6. Profile fields:** Besides instruments and genres, what should a profile show? For example display name, photo, short bio, age range, skill level, years playing, influences or favourite bands, gear, links to SoundCloud, YouTube, Spotify or Instagram.
> display name, photo, short bio, age range, skill level, years playing, influences or favourite bands, gear, links to SoundCloud, YouTube, Spotify or Instagram. Also general location, not specific.

**7. Instruments and genres:** Should users pick from a fixed list (easier to filter), type their own (more flexible), or both?
> Yeah a fixed dropdown list would be nice.

**8. Skill level:** Do you want a skill level such as Beginner / Intermediate / Advanced / Pro? Should it be set per instrument, or one level for the whole person?
> Yeah, include a skill level filter dropdown

**9. Location:** How exact should location be? Options are county only, Dublin area (Northside / Southside / Dublin 1–24), town, or "within X km". Should people be able to hide it?
> Lets just do county for now.

**10. Availability and goals:** Should profiles say what the person wants? For example casual jams, forming an original band, joining a covers or wedding band, session or paid work, or recording only. And when they're free, such as weeknights or weekends?
> Yes, something to differentiate casual to serious, band to wedding band.

## The posting forum

**11. Post types:** What kinds of posts should there be? For example "Looking for a band", "Band looking for a member", "Jam session", "Gig / dep needed", "Rehearsal space available".
> Yeah a general posting forum but with filters to look for specific type of players like one for lead guitar, bass, drums etc. Filter county etc.

**12. Post contents:** What does a post need? For example title, description, instruments wanted, genres, location, commitment level, and an optional expiry date.
> title, description, instruments wanted, genres, location, commitment level, and an optional expiry date.

**13. Replies:** Should people reply in public comments under the post, or contact the poster privately?
> Reply below in a comment section.

**14. Expiry:** Should old posts close automatically (for example after 30 days), or stay until the poster closes them?
> Yes lets have a 30 day expiry

## Search, filtering and matching

**15. Filters:** Which filters matter most to you? For example instrument, genre, location, skill level, goal, availability, or post type.
> instrument, genre, location are the most important.

**16. Matching:** When you say "match their tastes", do you mean simple filtering? Or do you want a "match score" or "suggested for you" list based on shared genres and influences, a nearby location and the instruments they need?
> "suggested for you" would be a nice inclusion. Maybe like a most recommended near the top of the page.

## Contact and safety

**17. Messaging:** Should there be private messaging inside the site in the first version? Or would showing contact details or social links be enough to start?
> contact details or social links to start

**18. Safety:** Do you need ways to report or block users, or an admin who can remove posts? Should email addresses always stay hidden?
> Yes have a report a user option. There will be an admin account for the overall page. Only admins can create other admins. Admins can only delete users or other admins.

## Look and feel

**19. Design:** You said Boards.ie and Bandcamp feel dated. Is there a site whose look you like, such as Spotify, Discord or Tinder-style cards? Do you want dark mode, light mode or both? Any colours or a vibe (gritty, clean, playful)?
> A Spotify/Garage Band colour vibe would be cool initially. Yes include both a dark and light mode toggle.

**20. Pages for version one:** Which pages must the first version have? My suggested minimum is a home/landing page, sign up / log in, a profile page, edit profile, a list of posts with filters, a single post page, and a create-post page. Should I add or remove any?
> home/landing page, sign up / log in, a profile page, edit profile, a list of posts with filters, a single post page, and a create-post page.

---

## Follow-up questions

Some answers needed a little more detail, so Claude asked these follow-ups.

**8a.** Should each person have one skill level overall, or one per instrument?
> per instrument

**10a.** For goals, two dropdowns (Commitment: Casual / Serious, plus Project type: Original band / Covers band / Wedding band / Jam only / Session work), or one combined list?
> two dropdowns

**10b.** Should profiles show availability (weeknights / weekends / flexible), or leave it out?
> include

**14a.** You chose a 30-day expiry and also an optional expiry date. Should 30 days be the default and the maximum, with posters able to pick an earlier date?
> 30 is the default and max

**17a.** Social links only, or also an optional public email or phone number?
> Social links only, also an optional public email or phone number

**18a.** Can admins also delete posts and comments, or only user accounts?
> Yes admins can delete posts or comments. The comment is still their but the content of the comment is removed for users to see and a 'admin removed' tag is visible.

**20a.** Your page list doesn't include an admin page, but admins need somewhere to see reports and delete users. Should I add a simple admin page?
> Yes include a simple admin page for maintenance.

## Delete rule questions

**1–3.** When a user is deleted, what happens to their posts, their comments, and reports they made or that are about them?
> SET NULL. I want to see the records but specify that the user is deleted.

**4.** When a user is deleted, what happens to the instruments and genres on their profile?
> CASCADE

**5.** When a post is deleted, what happens to its comments and its instrument and genre tags?
> CASCADE

**6.** When an instrument, genre or county is removed from a dropdown list, what happens to the users and posts that use it?
> RESTRICT
