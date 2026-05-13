# Engine Implementation Errors

## YouTube (yt-dlp)
- **Status:** ✅ SUCCESS
- **Result:** Successfully fetched trending video titles using `ytsearch`.

## Twitter (Tweepy)
- **Status:** ❌ FAILED (Error 401 Unauthorized)
- **Traceback:**
```
tweepy.errors.Unauthorized: 401 Unauthorized
```
- **Reasoning:** 
  The Twitter API returned a 401 error using the provided Consumer Keys and Access Tokens. This usually happens if:
  1. The keys are invalid or have been regenerated.
  2. The App does not have 'Read' permissions enabled in the Twitter Developer Portal (Settings -> User authentication settings).
  3. The App is not enabled for the V2 API (though most new apps are).
- **Recommended Action:** 
  User should verify that the App has **"Read"** permissions and that the **"User authentication settings"** are configured (even for a bot, it needs to be 'OAuth 1.0a' enabled for some endpoints). 
  Alternatively, providing a **Bearer Token** is often more reliable for recent searches.

## Final Note
The YouTube engine is ready and active. The Twitter engine is implemented but will log `twitter_tweepy_failed` until the credentials/permissions are fixed in the portal.
