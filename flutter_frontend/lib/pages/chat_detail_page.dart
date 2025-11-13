import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';
import '../models/message.dart';
import '../themes/colors.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/image_service.dart';
import '../services/storage_service.dart';
import '../widgets/frosted_glass_textfield.dart';

class ChatDetailPage extends StatefulWidget {
  final String roomId;
  final String roomName;

  const ChatDetailPage({required this.roomId, required this.roomName});

  @override
  State<ChatDetailPage> createState() => _ChatDetailPageState();
}

class _ChatDetailPageState extends State<ChatDetailPage> {
  late WebSocketChannel _channel;
  final _messageController = TextEditingController();
  final _messages = <Message>[];
  late String _currentUsername;
  bool _isConnecting = true;
  bool _hasError = false;
  String _errorMessage = '';
  late ScrollController _scrollController;

  @override
  void initState() {
    super.initState();
    _scrollController = ScrollController();
    _initializeChat();
  }

  Future<void> _initializeChat() async {
    try {
      final storageService = getStorageService();
      final token = await storageService.read(key: 'auth_token');
      if (token == null) {
        if (mounted) {
          setState(() {
            _hasError = true;
            _errorMessage = 'Token not found, please login again';
            _isConnecting = false;
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(_errorMessage)),
          );
        }
        return;
      }

      _currentUsername = getUsernameFromToken(token) ?? 'User';

      try {
        _channel = WebSocketChannel.connect(
          Uri.parse('$wsUrl?token=$token&room_id=${widget.roomId}'),
        );

        await _loadMessages();

        _channel.stream.listen(
          (event) {
            _handleWebSocketMessage(event);
          },
          onError: (error) {
            print('[ChatPage] WebSocket error: $error');
            if (mounted) {
              setState(() {
                _hasError = true;
                _errorMessage = 'WebSocket connection error: $error';
              });
            }
          },
          onDone: () {
            print('[ChatPage] WebSocket closed');
          },
        );

        if (mounted) {
          setState(() => _isConnecting = false);
        }
      } catch (e) {
        print('[ChatPage] Failed to connect to WebSocket: $e');
        if (mounted) {
          setState(() {
            _hasError = true;
            _errorMessage = 'Failed to connect to chat: $e';
            _isConnecting = false;
          });
        }
      }
    } catch (e) {
      print('[ChatPage] Error in _initializeChat: $e');
      if (mounted) {
        setState(() {
          _hasError = true;
          _errorMessage = 'Initialization error: $e';
          _isConnecting = false;
        });
      }
    }
  }

  Future<void> _loadMessages() async {
    try {
      final res = await apiClient.getRoomMessages(int.parse(widget.roomId));
      _messages.clear();
      for (var item in res) {
        _messages.add(Message.fromJson(item));
      }
      if (mounted) {
        setState(() {});
        _scrollToBottom();
      }
    } catch (e) {
      print('Error loading messages: $e');
    }
  }

  void _handleWebSocketMessage(dynamic event) {
    try {
      final data = jsonDecode(event);

      if (data['type'] == 'message') {
        final msg = Message.fromJson(data['message']);
        if (mounted) {
          setState(() {
            _messages.add(msg);
          });
          _scrollToBottom();
        }
      }
    } catch (e) {
      print('Error parsing WebSocket message: $e');
    }
  }

  Future<void> _scrollToBottom() async {
    await Future.delayed(Duration(milliseconds: 100));
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty) return;

    print('[Chat] Sending message: $text');
    _messageController.clear();

    try {
      print('[Chat] Room ID: ${widget.roomId}');
      final result =
          await apiClient.postRoomMessage(int.parse(widget.roomId), text);
      print('[Chat] Message sent successfully: $result');
      _scrollToBottom();
    } catch (e) {
      print('[Chat] Error sending message: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  List<TextSpan> _buildMessageSpans(String content) {
    final List<TextSpan> spans = [];
    final RegExp mentionRegex = RegExp(r'@[\w]+');

    int lastIndex = 0;
    for (final match in mentionRegex.allMatches(content)) {
      if (match.start > lastIndex) {
        spans.add(
          TextSpan(
            text: content.substring(lastIndex, match.start),
            style: TextStyle(
              fontSize: 16,
              color: kTextDark,
              fontFamily: 'Satoshi',
            ),
          ),
        );
      }
      spans.add(
        TextSpan(
          text: match.group(0),
          style: TextStyle(
            fontSize: 16,
            color: kTextDark,
            fontFamily: 'Satoshi',
            fontWeight: FontWeight.w700,
          ),
        ),
      );

      lastIndex = match.end;
    }

    if (lastIndex < content.length) {
      spans.add(
        TextSpan(
          text: content.substring(lastIndex),
          style: TextStyle(
            fontSize: 16,
            color: kTextDark,
            fontFamily: 'Satoshi',
          ),
        ),
      );
    }

    if (spans.isEmpty) {
      spans.add(
        TextSpan(
          text: content,
          style: TextStyle(
            fontSize: 16,
            color: kTextDark,
            fontFamily: 'Satoshi',
          ),
        ),
      );
    }

    return spans;
  }

  Future<void> _uploadImage() async {
    try {
      final imageFile = await ImageService.showImagePickerDialog(context);
      if (imageFile != null) {
        final isValid = await ImageService.isImageSizeValid(imageFile);
        if (!isValid) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Image size must be less than 5MB')),
            );
          }
          return;
        }

        // TODO: upload image to server and send as message
        // final base64Image = await ImageService.imageToBase64(imageFile);
        // await apiClient.postRoomMessage(int.parse(widget.roomId), base64Image);

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Image uploaded successfully')),
          );
        }
      }
    } catch (e) {
      print('Error uploading image: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to upload image: $e')),
        );
      }
    }
  }

  void _showInviteDialog() {
    final inviteController = TextEditingController();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Invite User to Room'),
        content: TextField(
          controller: inviteController,
          decoration: InputDecoration(
            hintText: 'Enter username',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              final username = inviteController.text.trim();
              if (username.isNotEmpty) {
                await _inviteUser(username);
                if (mounted) {
                  Navigator.pop(context);
                }
              }
            },
            child: Text('Invite'),
          ),
        ],
      ),
    );
  }

  Future<void> _inviteUser(String username) async {
    try {
      await apiClient.inviteToRoom(int.parse(widget.roomId), username);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('User $username invited successfully')),
        );
      }
    } catch (e) {
      print('Error inviting user: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to invite user: $e')),
        );
      }
    }
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    _channel.sink.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // If there's an error during initialization, show error message
    if (_hasError) {
      return Scaffold(
        appBar: AppBar(
          title: Text('Chat - ${widget.roomName}'),
        ),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 64, color: Colors.red),
              SizedBox(height: 16),
              Text(
                'Connection Error',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                _errorMessage,
                textAlign: TextAlign.center,
                style: TextStyle(color: kTextGray, fontFamily: 'Boska'),
              ),
              SizedBox(height: 24),
              ElevatedButton(
                onPressed: () {
                  Navigator.pop(context);
                },
                child: Text('Go Back'),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        flexibleSpace: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Theme.of(context).brightness == Brightness.dark
                    ? Colors.black.withOpacity(0.3)
                    : Colors.black.withOpacity(0.15),
                Colors.transparent,
              ],
            ),
          ),
        ),
        title: Text(
          widget.roomName,
          style: TextStyle(
            fontFamily: 'Boska',
            fontSize: 28,
            fontWeight: FontWeight.w700,
          ),
        ),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(Icons.person_add),
            onPressed: _showInviteDialog,
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: _isConnecting
                ? Center(child: CircularProgressIndicator())
                : _messages.isEmpty
                    ? Center(
                        child: Text(
                          'No messages yet',
                          style: TextStyle(
                              color: kTextGray, fontFamily: 'Satoshi'),
                        ),
                      )
                    : ListView.builder(
                        controller: _scrollController,
                        reverse: false,
                        itemCount: _messages.length,
                        itemBuilder: (_, i) {
                          final msg = _messages[i];
                          final isCurrentUser =
                              msg.username == _currentUsername;

                          return Align(
                            alignment: isCurrentUser
                                ? Alignment.centerRight
                                : Alignment.centerLeft,
                            child: Container(
                              margin: EdgeInsets.symmetric(
                                vertical: 6,
                                horizontal: 12,
                              ),
                              padding: EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: isCurrentUser ? kUserBubble : kBotBubble,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              constraints: BoxConstraints(
                                maxWidth:
                                    MediaQuery.of(context).size.width * 0.75,
                              ),
                              child: Column(
                                crossAxisAlignment: isCurrentUser
                                    ? CrossAxisAlignment.end
                                    : CrossAxisAlignment.start,
                                children: [
                                  if (!isCurrentUser)
                                    Text(
                                      msg.username,
                                      style: TextStyle(
                                        fontFamily: 'Boska',
                                        fontWeight: FontWeight.w700,
                                        fontSize: 12,
                                        color: kTextDark,
                                      ),
                                    ),
                                  SizedBox(height: 4),
                                  RichText(
                                    text: TextSpan(
                                      children: _buildMessageSpans(msg.content),
                                    ),
                                  ),
                                  SizedBox(height: 4),
                                  Text(
                                    msg.formattedTime,
                                    style: TextStyle(
                                      fontFamily: 'Satoshi',
                                      fontSize: 11,
                                      color: kTextGray,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
          ),
          // LLM 提示信息
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: kSecondary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: kSecondary.withOpacity(0.3),
                  width: 1,
                ),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: kSecondary, size: 18),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Type "@gro " to ask the AI assistant',
                      style: TextStyle(
                        fontSize: 12,
                        color: kSecondary,
                        fontFamily: 'Satoshi',
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: EdgeInsets.all(16),
            child: Row(
              children: [
                // 圖片上傳按鈕
                Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: _uploadImage,
                    child: Container(
                      padding: EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: kSecondary.withOpacity(0.3),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: kSecondary.withOpacity(0.5),
                          width: 1,
                        ),
                      ),
                      child: Icon(Icons.image, color: kSecondary, size: 20),
                    ),
                  ),
                ),
                SizedBox(width: 8),
                Expanded(
                  child: FrostedGlassTextField(
                    controller: _messageController,
                    placeholder: 'Type a message...',
                  ),
                ),
                SizedBox(width: 8),
                Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: _sendMessage,
                    child: Container(
                      padding: EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: kPrimary,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(Icons.send, color: Colors.white),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
