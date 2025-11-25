import 'dart:convert';
import 'dart:io';
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/ai_event.dart';
import 'storage_service.dart';

const bool useAndroidEmulator = false;

final String apiBase = _getApiBase();
final String wsUrl = _getWsUrl();

String _getApiBase() {
  if (kIsWeb) {
    // Web: 使用 localhost:8000 for development
    // In production, change to your backend URL
    final backendHost = 'localhost';
    final backendPort = 8000;
    //return 'http://$backendHost:$backendPort/api';
    return 'https://groceryshopperai-52101160479.us-west1.run.app/api';
  } else if (useAndroidEmulator) {
    // Android Emulator
    //return 'http://10.0.2.2:8000/api';
    return 'https://groceryshopperai-52101160479.us-west1.run.app/api';
  } else {
    // iOS 或 macOS
    //return 'http://localhost:8000/api';
    return 'https://groceryshopperai-52101160479.us-west1.run.app/api';
  }
}

String _getWsUrl() {
  if (kIsWeb) {
    // Web: 使用 localhost:8000 for development
    // In production, change to your backend URL
    //return 'ws://localhost:8000/ws';
    return 'wss://groceryshopperai-52101160479.us-west1.run.app/ws';
  } else if (useAndroidEmulator) {
    // Android Emulator
    //return 'ws://10.0.2.2:8000/ws';
    return 'wss://groceryshopperai-52101160479.us-west1.run.app/ws';
  } else {
    // iOS 或 macOS
    //return 'ws://localhost:8000/ws';
    return 'wss://groceryshopperai-52101160479.us-west1.run.app/ws';
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
    final url = Uri.parse(apiBase + path);
    print('[ApiClient] POST ' +
        url.toString() +
        ' with body: ' +
        body.toString());
    final res =
        await http.post(url, headers: await _headers(), body: jsonEncode(body));
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
    final url = Uri.parse(apiBase + path);
    print('[ApiClient] GET ' + url.toString());
    final res = await http.get(url, headers: await _headers());
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw Exception('HTTP ${res.statusCode}');
    }
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> put(String path, Map body) async {
    final url = Uri.parse(apiBase + path);
    print(
        '[ApiClient] PUT ' + url.toString() + ' with body: ' + body.toString());
    final res =
        await http.put(url, headers: await _headers(), body: jsonEncode(body));
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

  Future<void> delete(String path) async {
    final url = Uri.parse(apiBase + path);
    print('[ApiClient] DELETE ' + url.toString());
    final res = await http.delete(url, headers: await _headers());
    print('[ApiClient] DELETE response: ${res.statusCode}');
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

  Future<void> deleteRoom(int roomId) async {
    return await delete('/rooms/$roomId');
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

  // AI Planner - Generate group plan
  Future<Map<String, dynamic>> generateAIPlan(int roomId,
      {String? goal}) async {
    final body = <String, dynamic>{'goal': goal ?? ''};
    print(
        '[ApiClient] Calling generateAIPlan for room $roomId with goal: $goal');
    return await post('/rooms/$roomId/ai-plan', body);
  }

  // AI Matcher - Suggest invites and roles
  Future<Map<String, dynamic>> generateAISuggestion(int roomId,
      {String? goal}) async {
    final body = <String, dynamic>{'goal': goal ?? ''};
    print(
        '[ApiClient] Calling generateAISuggestion for room $roomId with goal: $goal');
    return await post('/rooms/$roomId/ai-matching', body);
  }

  // Inventory Management
  Future<List<dynamic>> getInventory() async {
    final res = await get('/inventory');
    return res['items'] as List<dynamic>;
  }

  Future<void> upsertInventoryItem(String name, int stock, int safetyStock) async {
    await post('/inventory', {
      'product_name': name,
      'stock': stock,
      'safety_stock_level': safetyStock,
    });
  }

  Future<void> deleteInventoryItem(int productId) async {
    await delete('/inventory/$productId');
  }

  // Shopping List Management
  Future<List<dynamic>> getShoppingLists() async {
    final res = await get('/shopping-lists');
    return res['lists'] as List<dynamic>;
  }

  Future<void> createShoppingList(String title, String itemsJson) async {
    await post('/shopping-lists', {
      'title': title,
      'items_json': itemsJson,
    });
  }

  Future<void> archiveShoppingList(int listId) async {
    await delete('/shopping-lists/$listId');
  }

  // WebSocket Management
  WebSocketChannel? _channel;
  final _aiEventController = StreamController<AIEvent>.broadcast();
  final _messageController = StreamController<Map<String, dynamic>>.broadcast();
  
  Stream<AIEvent> get aiEventStream => _aiEventController.stream;
  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;

  void connectWebSocket(int roomId) {
    disconnectWebSocket(); // Ensure no existing connection

    final url = '$wsUrl?room_id=$roomId';
    print('[ApiClient] Connecting to WebSocket: $url');
    
    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      
      _channel!.stream.listen(
        (message) {
          print('[ApiClient] WS Message: $message');
          try {
            final data = jsonDecode(message);
            if (data['type'] == 'ai_event') {
              final event = AIEvent.fromJson(data);
              _aiEventController.add(event);
            } else if (data['type'] == 'message') {
              _messageController.add(data['message']);
            }
          } catch (e) {
            print('[ApiClient] WS Parse Error: $e');
          }
        },
        onError: (error) {
          print('[ApiClient] WS Error: $error');
        },
        onDone: () {
          print('[ApiClient] WS Closed');
        },
      );
    } catch (e) {
      print('[ApiClient] WS Connection Error: $e');
    }
  }

  void disconnectWebSocket() {
    if (_channel != null) {
      print('[ApiClient] Disconnecting WebSocket');
      _channel!.sink.close();
      _channel = null;
    }
  }
}

final apiClient = ApiClient();
