import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'storage_service.dart';

const bool useAndroidEmulator = false;

// 根據平台決定 API 端點
final String apiBase = _getApiBase();
final String wsUrl = _getWsUrl();

String _getApiBase() {
  if (kIsWeb) {
    // Web: 使用 localhost:8000 for development
    // In production, change to your backend URL
    final backendHost = 'localhost';
    final backendPort = 8000;
    return 'http://$backendHost:$backendPort/api';
  } else if (useAndroidEmulator) {
    // Android Emulator
    return 'http://10.0.2.2:8000/api';
  } else {
    // iOS 或 macOS
    return 'http://localhost:8000/api';
  }
}

String _getWsUrl() {
  if (kIsWeb) {
    // Web: 使用 localhost:8000 for development
    // In production, change to your backend URL
    return 'ws://localhost:8000/ws';
  } else if (useAndroidEmulator) {
    // Android Emulator
    return 'ws://10.0.2.2:8000/ws';
  } else {
    // iOS 或 macOS
    return 'ws://localhost:8000/ws';
  }
}

class ApiClient {
  String? token;

  Future<Map<String, String>> _headers() async {
    final h = {'Content-Type': 'application/json'};
    final t = token ?? await storage.read(key: 'token');
    print(
        '[ApiClient] Token: ${t != null ? "found (${t.substring(0, 20)}...)" : "null"}');
    if (t != null) h['Authorization'] = 'Bearer $t';
    return h;
  }

  Future<Map<String, dynamic>> post(String path, Map body) async {
    print('[ApiClient] POST $path with body: $body');
    final res = await http.post(Uri.parse(apiBase + path),
        headers: await _headers(), body: jsonEncode(body));
    print('[ApiClient] POST response: ${res.statusCode}');
    if (res.statusCode < 200 || res.statusCode >= 300) {
      String msg = res.body;
      try {
        final j = jsonDecode(res.body);
        if (j is Map && (j['detail'] != null || j['error'] != null)) {
          msg = (j['detail'] ?? j['error']).toString();
        } else {
          msg = jsonEncode(j);
        }
      } catch (_) {}
      throw Exception('HTTP ${res.statusCode}: $msg');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> get(String path) async {
    final res =
        await http.get(Uri.parse(apiBase + path), headers: await _headers());
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw Exception('HTTP ${res.statusCode}');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> put(String path, Map body) async {
    print('[ApiClient] PUT $path with body: $body');
    final res = await http.put(Uri.parse(apiBase + path),
        headers: await _headers(), body: jsonEncode(body));
    print('[ApiClient] PUT response: ${res.statusCode}');
    if (res.statusCode < 200 || res.statusCode >= 300) {
      String msg = res.body;
      try {
        final j = jsonDecode(res.body);
        if (j is Map && (j['detail'] != null || j['error'] != null)) {
          msg = (j['detail'] ?? j['error']).toString();
        } else {
          msg = jsonEncode(j);
        }
      } catch (_) {}
      throw Exception('HTTP ${res.statusCode}: $msg');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<List<dynamic>> getRooms() async {
    final res = await get('/rooms');
    return res['rooms'] as List<dynamic>;
  }

  Future<List<dynamic>> getRoomMessages(int roomId) async {
    final res = await get('/rooms/$roomId/messages');
    return res['messages'] as List<dynamic>;
  }

  Future<List<dynamic>> getRoomMembers(int roomId) async {
    final res = await get('/rooms/$roomId/members');
    return res['members'] as List<dynamic>;
  }

  Future<Map<String, dynamic>> postRoomMessage(
      int roomId, String content) async {
    return await post('/rooms/$roomId/messages', {'content': content});
  }

  Future<Map<String, dynamic>> createRoom(String name) async {
    return await post('/rooms', {'name': name});
  }

  Future<Map<String, dynamic>> inviteToRoom(int roomId, String username) async {
    return await post('/rooms/$roomId/invite', {'username': username});
  }

  Future<Map<String, dynamic>> getLLMModel() async {
    // 偵測平台
    String platform = 'desktop';
    if (kIsWeb) {
      platform = 'web';
    } else if (Platform.isIOS) {
      platform = 'ios';
    } else if (Platform.isAndroid) {
      platform = 'android';
    }

    return await get('/users/llm-model?platform=$platform');
  }

  Future<Map<String, dynamic>> updateLLMModel(String model) async {
    return await put('/users/llm-model', {'model': model});
  }

  Future<Map<String, dynamic>> downloadTinyLlama() async {
    return await post('/models/download-tinyllama', {});
  }

  Future<Map<String, dynamic>> getDownloadProgress() async {
    return await get('/models/download-progress');
  }
}

final apiClient = ApiClient();
