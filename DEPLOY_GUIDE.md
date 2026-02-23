# 🚀 Deploy Holy Places CMS — Step by Step

This guide will get your site **live on the internet** in ~10 minutes so your friend can visit it and test the admin panel.

---

## STEP 1: Push Code to GitHub

### 1a. Create a GitHub Repository
1. Go to **https://github.com/new**
2. Repository name: `holy-places-cms`
3. Keep it **Public** (so Render can access it free)
4. **Don't** add README (we already have one)
5. Click **Create repository**

### 1b. Upload the Files
**Option A — Upload via browser (Easiest):**
1. On your new repo page, click **"uploading an existing file"**
2. Drag and drop the **entire `holy-places-cms` folder contents** (not the folder itself — open it and select all files/folders inside)
3. Click **Commit changes**

**Option B — Using Git command line:**
```bash
cd holy-places-cms
git init
git add .
git commit -m "Initial commit - Holy Places CMS"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/holy-places-cms.git
git push -u origin main
```

✅ Your code is now on GitHub!

---

## STEP 2: Deploy Live on Render (Free)

### 2a. Create Render Account
1. Go to **https://render.com**
2. Click **Get Started for Free**
3. Sign up with your **GitHub account** (this makes linking easy)

### 2b. Create a New Web Service
1. In Render dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub account if not already connected
3. Find and select your **`holy-places-cms`** repository
4. Click **Connect**

### 2c. Configure the Service
Fill in these settings:

| Setting | Value |
|---------|-------|
| **Name** | `holy-places-cms` (or any name you like) |
| **Region** | Pick closest to you (Singapore for India) |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT` |
| **Instance Type** | **Free** |

### 2d. Add Environment Variable
1. Scroll to **Environment Variables**
2. Click **Add Environment Variable**
3. Key: `SECRET_KEY`, Value: Click **Generate** (or type any random long string)

### 2e. Deploy
1. Click **"Create Web Service"**
2. Wait 2-3 minutes for the build to complete
3. You'll get a URL like: **`https://holy-places-cms.onrender.com`**

✅ Your site is now LIVE!

---

## STEP 3: Share with Your Friend

Send your friend these links:

| What | URL |
|------|-----|
| **Website** | `https://holy-places-cms.onrender.com` |
| **Admin Panel** | `https://holy-places-cms.onrender.com/admin` |
| **Login** | Username: `admin` / Password: `admin123` |

Your friend can:
- Browse the frontend with all holy places
- Log into the admin panel
- Add/edit places, modules, entries
- Upload media files
- Create new users and tags

---

## ⚠️ Important Notes

### Free Tier Limitations
- Render free tier **spins down after 15 min of inactivity** — first visit after idle takes ~30 seconds to wake up
- SQLite database **resets on redeploy** (for production, upgrade to PostgreSQL)
- 750 free hours/month (plenty for demo)

### To Keep Data Persistent (Optional)
If you want uploaded content to persist across redeployments, upgrade to Render's paid plan ($7/month) and attach a persistent disk, or switch the database to Render PostgreSQL (also free tier available).

### Security Reminder
Since this is a public demo:
- Change the admin password after deploying
- Don't upload sensitive content
- The demo credentials in the login page are visible to everyone

---

## 🔄 How to Update

After making changes locally:
```bash
git add .
git commit -m "Update description"
git push
```
Render will **automatically redeploy** within 1-2 minutes.

---

## 📱 Share as Mobile App (Bonus)

Your friend can "install" it as an app on their phone:
1. Open the site URL in Chrome (Android) or Safari (iOS)
2. Tap the browser menu → **"Add to Home Screen"**
3. It appears as a standalone app with the 🪷 icon!

This works because we included the PWA manifest.

---

That's it! Your Holy Places CMS is live on the internet. 🙏
