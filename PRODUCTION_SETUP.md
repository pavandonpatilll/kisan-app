# Production Setup

## Secrets

- Rotate the Gemini API key that was exposed in the shared conversation, then update the deployment environment with the replacement. Do not commit `.env` or service-account credentials.
- Configure `NEWSDATA_API_KEY` in the deployment environment; the NewsData key has been removed from source. Rotate the previously embedded key as well.
- Set `ADMIN_SESSION_SECRET` to a cryptographically random value of at least 32 bytes. Farmer sessions expire after 7 days; admin sessions expire after 30 minutes.
- Configure either `ADMIN_USERNAME` and `ADMIN_PASSWORD` in the deployment environment or a non-default Firestore admin account. The former hardcoded/default admin account is disabled.
- Set `FRONTEND_ORIGINS` to the exact HTTPS origins hosting `index.html` and `admin.html`.
- Configure the Razorpay key ID, key secret, and webhook secret in the deployment environment.

## Firebase Storage

- Create or select a Firebase Storage bucket and set `FIREBASE_STORAGE_BUCKET` to its exact bucket name from Firebase Console. Do not guess the bucket suffix.
- Grant the service account used by this API permission to create objects in that bucket.
- New chat images are stored under `chat/` in Cloud Storage, and their URLs are stored in Firestore chat messages. Keep a bucket lifecycle policy from deleting those objects if chat photos must remain available.
- Download-token URLs are durable bearer links: anyone who has a link can view that image. Existing `/uploads/chat/` files are still served for compatibility, but local-disk files on an ephemeral host are not permanent and are not migrated by this change.

## Deployment Check

- Deploy the backend and frontend together so the admin panel sends its signed session token and the farmer mandi ticker uses `/mandi-feed`.
- Farmers and admins must log in again once after deployment; pre-token saved sessions are intentionally not accepted.
- Verify admin login, dashboard reads, one admin write, farmer registration/login, direct and crop-group text/image chat, and the Razorpay test-mode flow before enabling live payments.
- Existing pending 6-month/yearly subscriptions created before subscription ownership notes were added may not pass the new user/plan ownership check. Let those checkouts complete or expire before deploying the backend change.