# Daily Sumati Satakam poster — setup guide

Every morning (06:30 IST by default) this project:

1. Picks the day's padyam (1 → 100 in order, from `start_date`).
2. Makes a 1080×1920 video (padyam + భావం, tanpura and temple bell) and a 1080×1350 image card.
3. **Posts automatically** to your **Instagram** (Reel) and **YouTube** channel (Short).
4. Publishes a **share page** on your phone (`https://<github-user>.github.io/<repo>/`), so **WhatsApp Status, WhatsApp Community and your Facebook profile** take two taps each.
5. Optionally pings your phone ("today's padyam is ready").

Everything runs free on GitHub. Your computer doesn't need to be on.

> **Why WhatsApp and the Facebook profile aren't fully automatic:** WhatsApp has no official way for apps to post statuses or community messages. Facebook stopped allowing apps to post on personal profiles in 2018. Unofficial tools exist but break WhatsApp's terms and can get your number banned. The share page is the safe alternative.

---

## Step 1 — Put the project on GitHub (10 min)

1. Create a free account at github.com, if you don't have one.
2. Click **New repository**, name it e.g. `sumati-daily`, and make it **Public**. GitHub Pages is free only for public repos, and your passwords and tokens are stored separately as private *Secrets*.
3. Click **uploading an existing file** and drag in **everything from this zip**, including the hidden `.github` folder. If your file browser hides it, upload `.github/workflows/daily.yml` separately via **Add file → Create new file** and paste its contents.
4. Go to **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**.

## Step 2 — Edit `config.json` (2 min)

Click `config.json` → ✏️ edit:

| Setting | What to put |
|---|---|
| `handle` | Your Instagram handle, shown at the bottom of every video |
| `start_date` | The day padyam 1 should go out, e.g. `"2026-10-20"` |
| `skip_flagged` | `true` to skip the 18 verses flagged below (2 more are always skipped) |
| `extra_skip` | Any verse numbers you want skipped, e.g. `[8, 42]` |
| `after_last` | `"repeat"` (start again after the last one) or `"stop"` |
| `text_animation` | `"typewriter"` (letter by letter, default) or `"fade"` (line by line) |
| `typing` | Typing speed in Telugu letters per second, separately for padyam (default 9) and భావం (default 16) |
| `sound.music` | `"tanpura"` (built in), `"none"`, or a file path such as `"music/flute.mp3"` (upload the mp3 to the repo) |
| `sound.bell` | `true`/`false` — temple bell at the start |
| `post_to` | Turn platforms on or off: `instagram`, `instagram_story`, `youtube`, `facebook_page` |
| `youtube_privacy` | `"public"`, or `"unlisted"` while testing |
| `ntfy_topic` | Optional phone reminder (see Step 6) |

To change the **posting time**, edit the `cron` line in `.github/workflows/daily.yml`. It's in UTC (IST − 5:30): `"0 1 * * *"` = 06:30 IST, `"30 0 * * *"` = 06:00 IST, `"30 13 * * *"` = 19:00 IST. GitHub sometimes starts runs 10–30 minutes late.

## Step 3 — Connect Instagram (20 min)

1. In the Instagram app: **Settings → Account type and tools → Switch to professional account** (Creator is fine).
2. Go to **developers.facebook.com** → log in → **My Apps → Create app**.
   * Use case: **"Manage messaging & content on Instagram"**. Type: Business. Any app name.
3. In the app: **Instagram → API setup with Instagram login → Add account**, then log in with your Instagram.
4. Click **Generate token** next to your account. Copy the **access token** and the **Instagram user ID** (both are shown on that screen).
   * You don't need App Review, because you're only posting to your own account, which is a tester of your own app.
5. In GitHub: **Settings → Secrets and variables → Actions → New repository secret**:
   * `IG_USER_ID` = the ID
   * `IG_ACCESS_TOKEN` = the token

**Token expiry:** Instagram tokens last 60 days. The job refreshes it every Monday. For the refreshed token to be saved automatically, also add a secret `GH_PAT`: a GitHub *fine-grained personal access token* for this repo with **Secrets: Read and write** permission. Without it, regenerate the token (step 4) every ~50 days.

## Step 4 — Connect YouTube (20 min, one time)

1. Go to **console.cloud.google.com** → create a project (e.g. "padyam").
2. **APIs & Services → Library →** search **YouTube Data API v3 → Enable**.
3. **OAuth consent screen →** External → fill in the app name and your email → add yourself as a test user → Save.
   Then click **Publish app → In production**. This matters: in "Testing" mode Google expires the sign-in after 7 days. You'll see an "unverified app" warning when you sign in; that's normal for a personal tool. Click *Advanced → Continue*.
4. **Credentials → Create credentials → OAuth client ID →** type **Desktop app** → Download the JSON.
5. On your computer (needs Python):
   ```
   pip install google-auth-oauthlib
   python youtube_auth.py client_secret_xxx.json
   ```
   Sign in with the Google account that owns your channel. It prints three values.
6. Add them as GitHub secrets: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

## Step 5 — Test it

1. GitHub → **Actions → Daily padyam → Run workflow**. Tick **dry_run** and run.
   It builds the video and share page without posting. Open the share page link shown on the run, on your phone.
2. Run again with **verse** = `1` and dry_run off. It posts for real. Check Instagram and YouTube.
3. From then on it runs by itself every morning. Each post is recorded in `state/posted_log.csv`, and a second run on the same day never double-posts.

If a platform fails, the run turns red and you get GitHub's failure email. The log line says why (usually an expired token).

## Step 6 — Your daily two taps (WhatsApp + Facebook profile)

1. On your phone, open `https://<github-user>.github.io/<repo>/` → browser menu → **Add to Home screen**.
2. Each morning, tap that icon:
   * **వీడియో షేర్ → WhatsApp → My status** (Status)
   * **ఫోటో + భావం షేర్ → WhatsApp →** your community's announcement group (Community)
   * **వీడియో షేర్ → Facebook →** Post/Reel (your profile)
   The padyam text is copied automatically, so long-press → Paste if the app doesn't fill it in.
3. **Optional reminder:** install the free **ntfy** app, subscribe to a made-up topic name (e.g. `badri-padyam-7392`), and put the same name in `ntfy_topic`. You'll get a notification each morning that opens the share page.

**Facebook profile alternative:** Instagram has a setting to share posts to Facebook automatically (**Accounts Center → Sharing across profiles**). It may not apply to posts made through the API, so check after the first post. If you'd rather have a Facebook **Page**, set `post_to.facebook_page: true` and add `FB_PAGE_ID` and `FB_PAGE_TOKEN` secrets; Pages can be posted to fully automatically.

---

## Verses flagged for review

The text was transcribed from the PDF and proofread verse by verse. These verses reflect 13th-century views that some followers may find offensive. **32 and 94 are skipped by default**; the rest post unless you set `skip_flagged: true` or list them in `extra_skip`. The PDF's own closing note says the same thing: take the good and leave what doesn't fit today.

| # | Opening line | Default | Why flagged |
|---|---|---|---|
| 8 | అల్లుని మంచితనంబును | posts | Caste name; view of women |
| 10 | ఆఁకలి యుడుగని కడుపును | posts | Prostitution, AIDS |
| 23 | ఒల్లని సతి నొల్లని పతి | posts | Caste name |
| 25 | కడు బలవంతుఁడైనను | posts | Prostitution |
| 32 | కసుగాయఁ గఱచి చూచిన | **skipped** | Sexual subject involving children |
| 35 | కాముకుఁడు దనిసి విడిచినఁ | posts | Sexual subject |
| 40 | కొక్కోక మెల్లఁ జదివిన | posts | Prostitution |
| 42 | కోమలి విశ్వాసంబునఁ | posts | "Women can't be trusted" |
| 55 | తలపొడుగు ధనము బోసిన | posts | Prostitution |
| 62 | నమ్మకు సుంకరి, జూదరి | posts | Distrust of a trade community, left-handed people |
| 64 | నరపతులు మేర దప్పినఁ | posts | Widows |
| 70 | పనిచేయు నెడల దాసియు | posts | Sexual reference; view of wives |
| 74 | పరునాత్మఁ దలఁచుసతి విడు | posts | Sexual reference |
| 76 | పర్వముల సతులఁ గవయకు | posts | Sexual reference |
| 77 | పలుదోమి సేయు విడియము | posts | Mild romantic reference |
| 78 | పాటెఱుఁగని పతి కొలువును | posts | Mild sexual reference |
| 81 | పిలువని పనులకుఁ బోవుట | posts | Sexual reference |
| 82 | పురికిని బ్రాణము కోమటి | posts | Caste name |
| 84 | పులిపాలు దెచ్చి యిచ్చిన | posts | Prostitution |
| 94 | మేలెంచని మాలిన్యుని | **skipped** | Derogatory caste names |

## Text corrections made from the PDF

* Verse 48: the PDF accidentally repeats line 3 of verse 47. The standard line (తడవోర్చిన నొడలోర్చినఁ) is used.
* Verse 93: line 2 is cut short in the PDF. The standard line is used.
* A handful of obvious typos in the PDF were corrected to standard readings (e.g. ధారాళమైన, తెలియుము). All verses are in `data/sumati.json`; edit any line there.

## About the భావం text

The poems are 800 years old and free to use. The **meanings (భావం) were written by Telugu Bhakti Pages (telugubhakti.com)**, so every post credits them (`credit_line` in config). If you'd rather avoid any question about reuse, either ask them for permission or replace the `bhavam` text in `data/sumati.json` with your own.

## Make a video on your own computer

```
pip install -r requirements.txt     # plus ffmpeg installed
python render.py 49                 # out/049.mp4, out/049.jpg, out/049.txt
python render.py 49 --music my.mp3 --no-bell
python daily.py --schedule 14       # see which padyam goes out each day
```
