# API Setup Guide / API 密钥获取指南

This guide walks you through getting API credentials for each platform.

---

## 1. Twitter/X

### Required Secrets
| Secret Name | Description |
|---|---|
| `TWITTER_API_KEY` | API Key (Consumer Key) |
| `TWITTER_API_SECRET` | API Secret (Consumer Secret) |
| `TWITTER_ACCESS_TOKEN` | Access Token |
| `TWITTER_ACCESS_SECRET` | Access Token Secret |

### Steps
1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new **Project** and **App**
3. In the App settings, go to **Keys and Tokens**
4. Generate **API Key and Secret** (Consumer Keys)
5. Generate **Access Token and Secret**
6. Make sure the App has **Read and Write** permissions:
   - Go to App Settings → User authentication settings → Set up
   - Select **Read and Write** under App permissions
7. Add all 4 values as GitHub repository secrets

> ⚠️ Twitter Free tier allows 1,500 tweets/month. Basic ($100/mo) allows 3,000.

---

## 2. Facebook

### Required Secrets
| Secret Name | Description |
|---|---|
| `FACEBOOK_PAGE_ID` | Your Facebook Page ID |
| `FACEBOOK_ACCESS_TOKEN` | Page Access Token (long-lived) |

### Steps
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new App (type: Business)
3. Add the **Facebook Login** product
4. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
5. Select your App, then click **Get User Access Token**
6. Select permissions: `pages_manage_posts`, `pages_read_engagement`
7. Click **Generate Access Token** and authorize
8. Exchange for a **long-lived token**:
   ```
   GET https://graph.facebook.com/v19.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id={APP_ID}&
     client_secret={APP_SECRET}&
     fb_exchange_token={SHORT_LIVED_TOKEN}
   ```
9. Get the **Page Access Token**:
   ```
   GET https://graph.facebook.com/v19.0/me/accounts?access_token={LONG_LIVED_USER_TOKEN}
   ```
10. Find your Page in the response — the `access_token` is your permanent Page Access Token
11. The `id` field is your `FACEBOOK_PAGE_ID`

---

## 3. Dev.to (V2 added 2026-05-25)

### Required Secrets
| Secret Name | Description |
|---|---|
| `DEVTO_API_KEY` | Dev.to API Key (free, instant) |

### Steps
1. Sign in to [Dev.to](https://dev.to/) (create account if you don't have one)
2. Go to [Settings → Extensions](https://dev.to/settings/extensions)
3. Scroll to **DEV Community API Keys**
4. Enter a description (e.g., `dibi8-auto-publisher`) and click **Generate API Key**
5. Copy the key as `DEVTO_API_KEY`

> 💡 Dev.to is the easiest setup — no OAuth, no approval, instant key. Rate limit 30/min.

> ⚠️ All Dev.to posts published by this tool will set `canonical_url` back to dibi8.com — no SEO duplicate content penalty.

---

## ⛔ Hashnode / LinkedIn / Medium (REMOVED 2026-05-25 V2)

- **Medium**: stopped issuing new integration tokens 2025-01-01
- **LinkedIn**: Marketing Developer Platform requires verified company page + $699+/month
- **Hashnode**: 2026 起 API 转 Pro plan, 免费版死 (测试时发现, 不在原 V2 plan)

三家都不适合个人开发者免费用。**Dev.to** 是当前唯一免费且 API 友好的开发者跨发平台。

---

## 5. Reddit

### Required Secrets
| Secret Name | Description |
|---|---|
| `REDDIT_CLIENT_ID` | App Client ID |
| `REDDIT_CLIENT_SECRET` | App Client Secret |
| `REDDIT_USERNAME` | Reddit username |
| `REDDIT_PASSWORD` | Reddit password |
| `REDDIT_SUBREDDIT` | Target subreddit (default: `artificial`) |

### Steps
1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. Click **Create App** or **Create Another App**
3. Fill in:
   - **Name**: dibi8-auto-publisher
   - **Type**: Select **script**
   - **Redirect URI**: `http://localhost:8080`
4. Click **Create App**
5. Note the **Client ID** (under the app name) and **Client Secret**
6. Use your Reddit login credentials for `REDDIT_USERNAME` and `REDDIT_PASSWORD`

> ⚠️ Be mindful of subreddit rules. Many subreddits have self-promotion limits.

---

## Adding Secrets to GitHub

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact name from the tables above

You only need to configure the platforms you want to use. Unconfigured platforms are automatically skipped.

---

## Testing

Run manually to test:

```bash
# Set environment variables
export TWITTER_API_KEY="your-key"
# ... set all variables for platforms you want to test

# Run the publisher
python run.py
```

Or trigger the workflow manually:
1. Go to **Actions** tab in your GitHub repo
2. Select **Auto Publish dibi8 Articles**
3. Click **Run workflow**
