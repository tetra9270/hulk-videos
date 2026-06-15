# Instagram Reels Automation System (Hulk Edition)

A robust, production-ready Python command-line application that automates publishing **five Instagram Reels per day** (specifically at 10:00 AM, 12:00 PM, 3:00 PM, 6:00 PM, and 10:00 PM) by pulling source videos from a public Google Drive folder or a local repository directory, uploading them to Cloudinary, and posting them via the Instagram Graph API.

---

## Architecture Overview

```
       ┌────────────────────────┐         ┌────────────────────────┐
       │   Local videos/ Folder │    OR   │  Public Drive Folder   │
       │   (No Google Cloud!)   │         │  (Shared publicly)     │
       └───────────┬────────────┘         └───────────┬────────────┘
                   │                                  │ (Using GOOGLE_API_KEY)
                   └────────────────┬─────────────────┘
                                    │ (Select next alphabetical unuploaded video)
                                    ▼
                        ┌────────────────────────┐
                        │ Retrieve video locally │ (Direct file copy or download)
                        └───────────┬────────────┘
                                    │ (Temporary path)
                                    ▼
                        ┌────────────────────────┐
                        │  Upload to Cloudinary  │
                        └───────────┬────────────┘
                                    │ (Get secure URL)
                                    ▼
                        ┌────────────────────────┐
                        │ Create Reels Container │ (Instagram Graph API)
                        └───────────┬────────────┘
                                    │ (Poll until processing is FINISHED)
                                    ▼
                        ┌────────────────────────┐
                        │      Publish Reel      │
                        └───────────┬────────────┘
                                    │
                   ┌────────────────┴────────────────┐
                   ▼                                 ▼
          ┌─────────────────┐               ┌─────────────────┐
          │  Update Local   │               │ Push history to │ (GitHub Actions
          │  history.json   │               │ Git Repository  │  stateless runs)
          └─────────────────┘               └─────────────────┘
```

---

## Features

- **5 Uploads Per Day**: Pre-configured schedule triggers at 10:00 AM, 12:00 PM, 3:00 PM, 6:00 PM, and 10:00 PM.
- **Hulk-Themed Captions**: Prepopulated with engaging, high-performing Hulk-themed captions inside `captions.txt`.
- **Google Cloud Bypass (Optional)**: Drop your videos directly inside a folder named `videos/` in your repository. The script will automatically parse them.
- **Google Drive Scraping Mode**: Fetches and downloads public videos without requiring any Google Service Account JSON files or OAuth authorization.
- **Git-Based History Tracking**: GitHub Actions commits and pushes the updated `history.json` back to your repo at the end of each run to save the upload state.
- **Self-Healing API connections**: Multi-layered retries for Meta Graph API container polling and network stability.

---

## Deployment & Scheduling Options

You can run this automation in two ways:

### Option 1: GitHub Actions (Recommended, 100% Free, Zero Setup)
This option runs headlessly inside GitHub's servers—you don't need a VPS, and your computer doesn't need to be turned on.

1. Create a repository on GitHub and upload your code.
2. Go to **Settings > Secrets and variables > Actions** and create the Repository Secrets:
   - `FACEBOOK_APP_ID`
   - `FACEBOOK_APP_SECRET`
   - `INSTAGRAM_ACCESS_TOKEN`
   - `INSTAGRAM_BUSINESS_ACCOUNT_ID`
   - `CLOUDINARY_CLOUD_NAME`
   - `CLOUDINARY_API_KEY`
   - `CLOUDINARY_API_SECRET`
   - `GOOGLE_DRIVE_FOLDER_ID` (Your shared folder ID)
   - `GOOGLE_API_KEY` (Leave empty if using public folder scraping)
3. The workflow file `.github/workflows/daily_upload.yml` is already set up to trigger **5 times a day** based on UTC.

#### Timezone Mapping for GitHub Actions (Cron Schedule)
GitHub Actions triggers schedules using **UTC (Coordinated Universal Time)**. We have mapped the cron hours to your target timezone:

* **For Indian Standard Time (IST - UTC+5:30):**
  The preconfigured cron is `'30 4,6,9,12,16 * * *'` which triggers at:
  - `04:30 UTC` = **10:00 AM IST**
  - `06:30 UTC` = **12:00 PM IST (noon)**
  - `09:30 UTC` = **03:00 PM IST**
  - `12:30 UTC` = **06:00 PM IST**
  - `16:30 UTC` = **10:00 PM IST**

* **For Pacific Time (PDT - UTC-7):**
  If you want these exact hours in Pacific Time, open `.github/workflows/daily_upload.yml` and change the cron schedule to:
  `cron: '0 1,5,17,22 * * *'` (triggers at 10 AM, 3 PM, 6 PM, and 10 PM PDT).

---

### Option 2: VPS Daemon Mode (AWS, DigitalOcean, local PC)
Use this option if you want to keep a background script running 24/7 on your own server.

1. Ensure your server environment has your credentials in the `.env` file.
2. Run the application in daemon mode:
   ```bash
    python main.py --daemon --time 10:00,12:00,15:00,18:00,22:00
   ```
3. The script will keep running in the background and trigger the upload exactly at the local server times listed.

---

## Customizing Captions (`captions.txt`)

You can define captions in `captions.txt` using `---` as a separator. 

The system supports two methods:
1. **Filename-Specific Mapping**: Prefix the caption with the exact filename and a colon.
   ```text
   my_hulk_video.mp4: Incredible Hulk smash scene! 🟢💥 #hulk #avengers
   ```
2. **Sequential Rotation fallback**: If no match is found, the system rotates through the list of captions sequentially based on the total number of uploaded videos in your history.
