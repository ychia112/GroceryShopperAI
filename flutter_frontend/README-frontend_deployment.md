# GroceryShopperAI Deployment Guide

This document explains how to **deploy the frontend (Flutter Web + Firebase Hosting)**  
and how to **build the mobile app (Android APK / iOS IPA)** for testing or release.

---

## Prerequisites

Before starting, make sure you have:

- **Flutter SDK ≥ 3.0**
- **Firebase CLI** installed
  
```bash
  npm install -g firebase-tools
```

- Access to the Firebase project: groceryshopperai
- Logged in to Firebase:

```bash
firebase login
```

## 1. Deploying Frontend to Firebase Hosting
### 1.1 Install dependencies

```bash
flutter pub get
```

### 1.2 Update backend API URLs

In lib/services/api_client.dart, confirm these lines:

```dart
// HTTPS endpoint (Cloud Run backend)
return 'https://groceryshopperai-52101160479.us-west1.run.app/api';

// WebSocket endpoint
return 'wss://groceryshopperai-52101160479.us-west1.run.app/ws';
```

### 1.3 Run locally to test

```bash
flutter run -d chrome
```

Make sure login, chatroom, and token saving all work correctly before deployment.

### 1.4 Build the web app
```bash
flutter build web
```

This generates static files under:
```build/web/```

### 1.5 Deploy to Firebase

```bash
firebase use groceryshopperai
flutter build web
firebase deploy --only hosting
```
When complete, you’ll see output like:
```

✔  Deploy complete!

Project Console: https://console.firebase.google.com/project/groceryshopperai
Hosting URL: https://groceryshopperai.web.app
```

Visit the Hosting URL to test your live production site.

### 1.6 Verify deployment

1. Open the Firebase Hosting URL
2. Try logging in / creating rooms / sending messages
3. Check DevTools → Network tab to confirm requests go to Cloud Run



## 2. Building the Mobile App (Android)
### 2.1 Build an APK for testing
```bash
flutter build apk --release
```

Output:
```
build/app/outputs/flutter-apk/app-release.apk
```

### 2.2 Share for internal testing

You can share the APK via:
- Google Drive
- Telegram / Discord
- USB file transfer

The tester must enable "Install from unknown sources" on their phone.

### 2.3 (Optional) Upload to Google Play Store
```bash
flutter build appbundle --release
```

Then go to Google Play Console to upload the .aab bundle (requires a $25 one-time developer registration fee).

### 3. Deploy again for milestone
Tip:
For milestone demos, always rebuild the web app before deploying to avoid serving cached files.

```bash
# 1. clean the old build cache
flutter clean

# 2. download all pachages again
flutter pub get

# 3. recompile（Release mode）
flutter build web --release

# 4. deploy to Firebase Hosting
firebase deploy --only hosting
```
