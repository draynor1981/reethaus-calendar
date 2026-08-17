# Reethaus Program → iPhone Calendar Feed

Self-updating calendar feed for the Reethaus / Flussbad program in Berlin.
Scrapes https://slowness.com/calendar/ once a day via GitHub Actions and
publishes `reethaus.ics`, which you subscribe to on your iPhone.

## Setup (one time, ~15 minutes)

### 1. Create a GitHub account
If you don't have one: https://github.com/signup (free).

### 2. Create the repository
- Go to https://github.com/new
- Repository name: `reethaus-calendar`
- Visibility: **Public** (required for free GitHub Pages)
- Click **Create repository**

### 3. Upload these files
On the new repo page, click **uploading an existing file** and drag in:
- `scraper.py`
- `requirements.txt`
- `README.md`

Then commit. The workflow file must be added separately because drag-and-drop
sometimes strips folders:
- Click **Add file → Create new file**
- Name it exactly: `.github/workflows/update.yml`
- Paste the contents of `update.yml` from this folder
- Commit

### 4. Run it once manually
- Go to the **Actions** tab of your repo
- If prompted, click **"I understand my workflows, enable them"**
- Select **Update Reethaus calendar** → **Run workflow** → **Run workflow**
- After ~1 minute it should show a green tick, and `reethaus.ics`
  appears in the repo file list

### 5. Enable GitHub Pages
- Repo **Settings → Pages**
- Under "Build and deployment": Source = **Deploy from a branch**,
  Branch = **main**, folder = **/ (root)** → **Save**
- After a minute your feed is live at:

  `https://YOUR-USERNAME.github.io/reethaus-calendar/reethaus.ics`

### 6. Subscribe on your iPhone
Settings → Calendar → Accounts → Add Account → Other →
**Add Subscribed Calendar**, and enter (note `webcal://`, not `https://`):

  `webcal://YOUR-USERNAME.github.io/reethaus-calendar/reethaus.ics`

Done. iOS refreshes subscribed calendars periodically; new Reethaus
events appear within a day or so of being announced.

## Maintenance

- **If new events stop appearing:** slowness.com probably changed their
  page layout. Check the Actions tab — a failing (red) run with
  "no events found" confirms it. The parser in `scraper.py` needs a
  small adjustment; the script deliberately refuses to overwrite the
  feed with an empty one, so your existing events stay intact meanwhile.
- **To change the schedule:** edit the `cron:` line in
  `.github/workflows/update.yml`.
- Note: GitHub automatically disables scheduled workflows in repos with
  no activity for 60 days. If that happens you'll get an email and can
  re-enable it with one click in the Actions tab.
