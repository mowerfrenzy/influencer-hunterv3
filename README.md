# Influencer Hunter Global — Windows 11

A local Streamlit prospecting workspace for finding and qualifying Instagram micro-influencers in the three pillars from your PDF: **Wealth, Health, Relationships**.

## What this version does
- Includes every niche and sub-niche from your uploaded prospecting PDF.
- Global targeting: no fixed country whitelist. It stores **creator country** separately from **audience countries**, because audience geography is more useful for commercial targeting.
- Generates search queries for selected niches and imports candidate Instagram URLs from Google Alerts RSS.
- Optional Apify connector to bulk-look up public profile data and recent posts from profile URLs. Paste your own Apify token; no Instagram login is used.
- Calculates engagement estimate from the average likes and comments returned for sampled posts.
- Can check a supplied creator website for publicly displayed emails, respecting robots.txt and staying on the same domain.
- Scores ICP evidence: niche, audience problem, trust, monetized offer, email source, follower range, engagement.
- Exports qualified leads and all candidates to CSV.

## Important reality check
This is a discovery + enrichment + qualification app, not a magic Instagram-wide crawler. It cannot guarantee 100–500 qualified leads or discover every matching creator automatically. Discovery is the bottleneck: use multiple search queries/feeds, then bulk-verify the resulting candidate URLs. Instagram does not provide a general public API for searching all arbitrary creators and exposing their audience demographics. Third-party Actors can change, fail, or be blocked, and their input/output schemas and charges vary.

The default Apify Actor ID is `apify/instagram-scraper`. The connector uses the Apify synchronous run-and-get-dataset-items endpoint. If the Actor's input schema changes, paste its current input JSON into the Advanced Actor input box. Test a tiny batch first and set a maximum cost in Apify Console before running a large batch. Third-party usage charges are separate from this free local app. Apify pricing and Actor availability can change; verify the current price on the Actor page before running.

Profile fields from Apify may include follower count and recent posts, but **audience country distribution is not reliably available from public profile data**. Enter audience countries only when supported by creator media kits, audience insights shared by the creator, or another legitimate evidence source. Do not infer audience geography from the creator's location or language.

## Qualification rules
Default hard filters:
- 10,000–100,000 followers.
- Engagement strictly above 3%: `(average likes + average comments) / followers × 100`.
- At least 5 recent posts sampled; inspect the sample manually and prefer 10–12+ consistent posts.
- Niche confirmed against your ICP list.
- Audience countries recorded from evidence (not assumed).
- Public business email and source URL recorded.
- Individual creator (not a brand) confirmed.
- Evidence that the creator has a monetized offer, product, service, membership, or commercial recommendation.
- Evidence of a real audience problem and audience trust.

The score is an internal prioritization aid, not proof of conversion probability. A high score does not override a failed hard filter.

## Install on Windows 11
1. Install Python 3.11 or newer from https://www.python.org/downloads/ (enable **Add Python to PATH**).
2. Extract this ZIP to `C:\InfluencerHunterGlobal`.
3. Open Command Prompt in that folder.
4. Run:
   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   streamlit run app.py
   ```
5. The dashboard opens at `http://localhost:8501`.

## Use it
1. Open **Discover** and import Google Alerts RSS results or download generated niche queries.
2. Paste candidate profile URLs/usernames into **Verify profiles**. Add an Apify token if you want bulk metric enrichment. Start with 5 profiles.
3. Open **Enrich & qualify**. Fill in niche, audience countries, email source URL, creator type, offer evidence, audience problem evidence and trust evidence. Import/export CSV as needed.
4. Open **Review & export**. Export qualified leads.

## Apify connector
- Create an Apify account and copy your API token from Apify Console → Settings → API & Integrations.
- The app submits a run to the Actor ID entered in the UI. Default is `apify/instagram-scraper`.
- If the default Actor expects a different input format in your account/current version, check the Actor's Input tab and paste the exact JSON into **Advanced Actor input**.
- Keep batches small initially. The Actor's cost model is per result/event and can differ by Actor. A profile plus posts may generate multiple billable records.
- Token is entered as a password field and is not saved to the CSV. Do not share screenshots containing your token.

## Email and legal safeguards
Only collect business contact emails the creator has publicly presented for professional inquiries. Keep the URL where the email appeared. Do not collect private emails from leaks, login-only pages, DMs, or data brokers. Website email lookup checks robots.txt, stays on the supplied domain, and limits pages. Before outreach, check applicable privacy and electronic marketing rules (including GDPR/UK GDPR, PECR, CAN-SPAM, CASL and local laws as applicable), identify yourself, and honour opt-outs.

## Troubleshooting
- **No RSS candidates:** broaden queries, create additional alerts, and ensure the feed URL is valid.
- **Apify API error:** verify token, Actor ID, Actor input schema, available credits and run limits.
- **No engagement:** some profiles hide likes or expose too few posts; leave unverified fields blank rather than guessing.
- **No public email:** keep the candidate unqualified until a public professional email is found.
