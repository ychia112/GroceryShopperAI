import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

// CONFIG
// If you run on Android emulator, set useAndroidEmulator = true to use
// 10.0.2.2 for localhost; otherwise use localhost for iOS/macos.
const bool useAndroidEmulator = false;
final String apiBase = useAndroidEmulator
    ? 'http://10.0.2.2:8000/api'
    : 'http://localhost:8000/api';
final String wsUrl = useAndroidEmulator
    ? 'ws://10.0.2.2:8000/ws'
    : 'ws://localhost:8000/ws';

final storage = FlutterSecureStorage();

class ApiClient {
  String? token;

  Future<Map<String, String>> _headers() async {
    final h = {'Content-Type': 'application/json'};
    final t = token ?? await storage.read(key: 'token');
    if (t != null) h['Authorization'] = 'Bearer $t';
    return h;
  }

  Future<Map<String, dynamic>> post(String path, Map body) async {
    final res = await http.post(Uri.parse(apiBase + path),
        headers: await _headers(), body: jsonEncode(body));
    if (res.statusCode < 200 || res.statusCode >= 300) {
      // try to surface useful error
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
    final res = await http.get(Uri.parse(apiBase + path), headers: await _headers());
    if (res.statusCode < 200 || res.statusCode >= 300) throw Exception('HTTP ${res.statusCode}: ${res.body}');
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<void> login(String u, String p) async {
    final out = await post('/login', {'username': u, 'password': p});
    token = out['token'];
    await storage.write(key: 'token', value: token);
  }

  Future<void> signup(String u, String p) async {
    final out = await post('/signup', {'username': u, 'password': p});
    token = out['token'];
    await storage.write(key: 'token', value: token);
  }

  Future<List<dynamic>> loadMessages() async {
    final out = await get('/messages');
    return out['messages'] as List<dynamic>;
  }

  Future<void> postMessage(String content) async {
    await post('/messages', {'content': content});
  }

  Future<void> logout() async {
    token = null;
    await storage.delete(key: 'token');
  }
}

class WsClient {
  WebSocketChannel? _channel;
  void Function(Map<String, dynamic>)? onMessage;
  bool connected = false;

  void connect(String url, {String? token}) {
    if (_channel != null) return; // already connected or connecting
    var uri = Uri.parse(url);
    if (token != null) {
      final q = Map<String, String>.from(uri.queryParameters)..['token'] = token;
      uri = uri.replace(queryParameters: q);
    }
    _channel = WebSocketChannel.connect(uri);
    connected = true;
    _channel!.stream.listen((data) {
      try {
        final json = jsonDecode(data as String) as Map<String, dynamic>;
        onMessage?.call(json);
      } catch (_) {}
    }, onDone: () {
      _channel = null;
      connected = false;
      // simple reconnect
      Future.delayed(Duration(seconds: 2), () => connect(url, token: token));
    }, onError: (_) {
      // ignore - onDone will handle reconnect
    });
  }

  void close() {
    try {
      _channel?.sink.close();
    } catch (_) {}
    _channel = null;
    connected = false;
  }
}

void main() {
  runApp(MyApp());
}

class MyApp extends StatefulWidget {
  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  final ApiClient api = ApiClient();
  final WsClient ws = WsClient();
  List<Map<String, dynamic>> messages = [];
  bool authed = false;
  String statusMsg = '';

  final TextEditingController userCtl = TextEditingController();
  final TextEditingController passCtl = TextEditingController();
  final TextEditingController chatCtl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tryRestore();
    ws.onMessage = (m) {
      if (m['type'] == 'message') {
        setState(() => messages.add(Map<String, dynamic>.from(m['message'])));
      }
    };
  }

  Future<void> _tryRestore() async {
    final tok = await storage.read(key: 'token');
    if (tok != null) {
      api.token = tok;
      try {
        final ms = await api.loadMessages();
        setState(() {
          messages = List<Map<String, dynamic>>.from(ms);
          authed = true;
        });
        ws.connect(wsUrl, token: api.token);
      } catch (_) {
        await api.logout();
        setState(() => authed = false);
      }
    }
  }

  Future<void> _login() async {
    try {
      await api.login(userCtl.text.trim(), passCtl.text);
      final ms = await api.loadMessages();
      setState(() {
        messages = List<Map<String, dynamic>>.from(ms);
        authed = true;
        statusMsg = '';
      });
      ws.connect(wsUrl, token: api.token);
    } catch (e) {
      setState(() => statusMsg = e.toString());
    }
  }

  Future<void> _signup() async {
    try {
      await api.signup(userCtl.text.trim(), passCtl.text);
      final ms = await api.loadMessages();
      setState(() {
        messages = List<Map<String, dynamic>>.from(ms);
        authed = true;
        statusMsg = '';
      });
      ws.connect(wsUrl, token: api.token);
    } catch (e) {
      setState(() => statusMsg = e.toString());
    }
  }

  Future<void> _send() async {
    final text = chatCtl.text.trim();
    if (text.isEmpty) return;
    chatCtl.clear();
    try {
      await api.postMessage(text);
    } catch (e) {
      setState(() => statusMsg = e.toString());
    }
  }

  Future<void> _logout() async {
    ws.close();
    await api.logout();
    setState(() {
      authed = false;
      messages = [];
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'GroceryChat',
      home: Scaffold(
        appBar: AppBar(title: Text('GroceryChat')),
        body: LayoutBuilder(
          builder: (context, constraints) {
            // breakpoint for desktop/web
            if (constraints.maxWidth >= 800) {
              return authed ? _buildChatDesktop(constraints.maxWidth) : _buildAuth();
            } else {
              return authed ? _buildChat() : _buildAuth();
            }
          },
        ),
      ),
    );
  }

  Widget _buildAuth() {
    return Padding(
      padding: EdgeInsets.all(16),
      child: Column(children: [
        TextField(controller: userCtl, decoration: InputDecoration(labelText: 'username')),
        SizedBox(height: 8),
        TextField(controller: passCtl, decoration: InputDecoration(labelText: 'password'), obscureText: true),
        SizedBox(height: 12),
        Row(children: [
          ElevatedButton(onPressed: _login, child: Text('Login')),
          SizedBox(width: 8),
          ElevatedButton(onPressed: _signup, child: Text('Sign up')),
        ]),
        SizedBox(height: 12),
        Text(statusMsg, style: TextStyle(color: Colors.red)),
      ]),
    );
  }

  Widget _buildChat() {
    return Column(children: [
      Expanded(
        child: ListView.builder(
          padding: EdgeInsets.all(12),
          itemCount: messages.length,
          itemBuilder: (_, i) {
            final m = messages[i];
            final isBot = m['is_bot'] == true;
            return Container(
              margin: EdgeInsets.symmetric(vertical: 6),
              padding: EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: isBot ? Colors.grey[200] : Colors.blue[50],
                borderRadius: BorderRadius.circular(6),
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${m['username'] ?? 'unknown'} • ${m['created_at'] ?? ''}', style: TextStyle(fontSize: 12, color: Colors.grey[700])),
                SizedBox(height: 6),
                Text('${m['content'] ?? ''}'),
              ]),
            );
          },
        ),
      ),
      Padding(
        padding: EdgeInsets.all(8),
        child: Row(children: [
          Expanded(child: TextField(controller: chatCtl, decoration: InputDecoration(hintText: 'Message'))),
          SizedBox(width: 8),
          ElevatedButton(onPressed: _send, child: Text('Send')),
          SizedBox(width: 8),
          ElevatedButton(onPressed: _logout, child: Text('Logout')),
        ]),
      ),
    ]);
  }

  // Desktop / web layout: sidebar + chat area
  Widget _buildChatDesktop(double width) {
    return Row(children: [
      Container(
        width: (width * 0.25).clamp(200, 320),
        color: Colors.grey[100],
        child: Column(
          children: [
            SizedBox(height: 12),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Rooms / Users', style: TextStyle(fontWeight: FontWeight.bold)),
                  IconButton(onPressed: () {}, icon: Icon(Icons.search)),
                ],
              ),
            ),
            Divider(height: 1),
            // Placeholder for rooms/users list
            Expanded(
              child: ListView.builder(
                itemCount: 6,
                itemBuilder: (_, i) => ListTile(
                  leading: CircleAvatar(child: Text('U${i+1}')),
                  title: Text('User ${i+1}'),
                  subtitle: Text('last message...'),
                ),
              ),
            ),
          ],
        ),
      ),
      VerticalDivider(width: 1),
      Expanded(child: _buildChat()),
    ]);
  }
}
