# Super Deals India – Instagram Autopost

Posts one branded Hinglish carousel to Instagram every day at **7:30 PM IST**, fully automatically.

```
content/calendar.csv  →  Gemini writes the slides  →  Pillow renders 1080×1350 JPEGs
      →  pushed to this repo (public image URLs)  →  Instagram API publishes the carousel
```

---

## One-time setup (about 45 minutes)

### Step 1 – Instagram account ✅ (done)
- @super_dealsindia is a professional (Creator) account, linked to the Super Deals India Facebook Page.
- Keep your Telegram/WhatsApp/website link in the bio. Every post's CTA says "link in bio".

### Step 2 – Meta app and token ✅ (set up 26 Nov 2026)
- App **superdealsindia_auto** is in the business portfolio **super_dealsindia**.
- System user **sdi-autopost-bot** has the app, the Super Deals India Page and the @super_dealsindia Instagram (Content + Insights).
- Instagram user ID: **17841473008835940**
- Token: Business Suite → Settings → **System users → sdi-autopost-bot → Generate token**
  → app *superdealsindia_auto*, expiry **Never**, permissions **instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement**.
  This token never expires, so nothing needs refreshing.

### Step 3 – Gemini API key (free)
1. Go to **aistudio.google.com → Get API key → Create API key**.
2. Copy the key.

### Step 4 – GitHub repo
1. Create a **new PUBLIC repository**, e.g. `sdi-instagram`.
   *Public is required: Instagram downloads the slide images from the repo. No passwords or keys are ever stored in the files; they live in GitHub Secrets.*
2. Upload all files from this folder (keep the folder structure, including `.github/`).
3. Repo → **Settings → Secrets and variables → Actions → New repository secret**, add:

| Secret name | Value |
|---|---|
| `GEMINI_API_KEY` | key from Step 3 |
| `IG_ACCESS_TOKEN` | system-user token from Step 2 |
| `IG_USER_ID` | `17841473008835940` |

4. Optional, under the **Variables** tab: `GEMINI_MODEL` (default `gemini-3.6-flash`), `IG_API_VERSION` (default `v24.0`), `IG_API_HOST` (default `graph.facebook.com`).
5. Repo → **Settings → Actions → General → Workflow permissions → Read and write permissions** → Save.

### Step 5 – Test once by hand
1. Repo → **Actions → Daily Instagram post → Run workflow**.
2. Enter a date from the calendar, e.g. `2026-12-01`, and click **Run**.
3. Watch the run. When it is green, the post is live, and `posts/posted.json` has the link.

After that it runs every day by itself.

---

## Day to day

- **Change what gets posted:** edit `content/calendar.csv` (columns: `date, pillar, topic, hook, points`; separate points with `|`, 3–7 points per post).
- **Calendar runs out on 30 Dec 2026.** Add next month's rows before then. If a date has no row, nothing is posted that day.
- **Check today's post:** look at the latest run under *Actions*, or at the slides in `posts/<date>/`.
- **A run failed?** GitHub emails you. Usual causes: the token was revoked in Business Suite (generate a new one and update the secret), Gemini quota, or a typo in the calendar.
- **Change the posting time:** edit the `cron` line in `.github/workflows/daily_post.yml` (it is in UTC; IST = UTC + 5:30).

## Local preview (optional, never posts)

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key
python -m ig_autopost.main preview --date 2026-12-07
# slides + caption appear in preview/2026-12-07/
```

## Safety built in
- Gemini is told not to invent prices, stats, sale dates or brand claims, and every answer is checked for length and structure (3 tries, otherwise the run fails and nothing is posted).
- A date is never posted twice (`posts/posted.json`).
- Instagram's limit is 100 API posts a day; this posts 1.

Fonts: Poppins and Inter, both under the SIL Open Font License (see `fonts/`).
