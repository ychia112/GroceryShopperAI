# Flutter Frontend for GroceryShopperAI

This folder contains a minimal Flutter app that replaces the existing vanilla JS frontend.

Files created:
- `pubspec.yaml` — declares dependencies (http, web_socket_channel, flutter_secure_storage).
- `lib/main.dart` — minimal chat client: login/signup, load messages, send message, WebSocket listener.

How to run
1. Install Flutter SDK and ensure `flutter` is on your PATH.
2. From project root or this folder:

```bash
cd /Users/ychia/GroceryShopperAI/flutter_frontend
flutter pub get
flutter run
```

Notes
- API endpoints default to `http://localhost:8000/api` and `ws://localhost:8000/ws` for macOS/iOS. If you run on Android emulator, open `lib/main.dart` and set `useAndroidEmulator = true` to use `10.0.2.2:8000`.
- The app stores the auth token in `flutter_secure_storage`.
- If your backend runs on a different host/port, edit the `apiBase` and `wsUrl` constants in `lib/main.dart`.

Next steps
- Improve error handling, loading states and push UI polish.
- Optionally swap to a state-management solution (Provider / Riverpod) for larger apps.
