import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_client.dart';
import '../providers/auth_provider.dart';
import '../themes/colors.dart';
import 'chat_detail_page.dart';

class ContactsPage extends StatefulWidget {
  @override
  State<ContactsPage> createState() => _ContactsPageState();
}

class _ContactsPageState extends State<ContactsPage> {
  List<Map<String, dynamic>> _rooms = [];
  Map<int, List<Map<String, dynamic>>> _roomMembers = {};
  Map<String, List<int>> _contactRooms = {};
  bool _isLoading = true;
  String? _selectedContact;
  late String _currentUsername;

  @override
  void initState() {
    super.initState();
    _initData();
  }

  Future<void> _initData() async {
    try {
      final authProvider = context.read<AuthProvider>();
      _currentUsername = authProvider.username ?? 'User';

      final rooms = await apiClient.getRooms();
      setState(() {
        _rooms = rooms
            .map((r) => {
                  'id': r['id'] as int,
                  'name': r['name'] as String,
                })
            .toList();
      });

      for (var room in _rooms) {
        final members = await apiClient.getRoomMembers(room['id']);
        final memberList = members
            .map((m) => {
                  'id': m['id'] as int,
                  'username': m['username'] as String,
                })
            .toList();

        setState(() {
          _roomMembers[room['id']] = memberList;
        });

        for (var member in memberList) {
          if (member['username'] != _currentUsername) {
            final username = member['username'] as String;
            if (!_contactRooms.containsKey(username)) {
              _contactRooms[username] = [];
            }
            _contactRooms[username]!.add(room['id']);
          }
        }
      }

      setState(() => _isLoading = false);
    } catch (e) {
      print('Error loading contacts: $e');
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load contacts: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (_isLoading) {
      return Scaffold(
        appBar: _buildGradientAppBar('Contacts'),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final contacts = _contactRooms.keys.toList();

    if (contacts.isEmpty) {
      return Scaffold(
        appBar: _buildGradientAppBar('Contacts'),
        body: Center(
          child: Text(
            'No contacts yet\nJoin a chat room to see contacts',
            textAlign: TextAlign.center,
            style: TextStyle(color: kTextGray, fontFamily: 'Satoshi'),
          ),
        ),
      );
    }

    if (_selectedContact != null) {
      return _buildContactDetail(isDark, _selectedContact!);
    }

    return Scaffold(
      appBar: _buildGradientAppBar('Contacts'),
      body: ListView.builder(
        itemCount: contacts.length,
        itemBuilder: (context, index) {
          final username = contacts[index];
          return ListTile(
            leading: CircleAvatar(
              radius: 24,
              backgroundColor: isDark ? Colors.grey[800] : Colors.grey[300],
              child: Text(
                username[0].toUpperCase(),
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : Colors.black,
                ),
              ),
            ),
            title: Text(username),
            subtitle: Text(
              '${_contactRooms[username]!.length} shared chat room${_contactRooms[username]!.length == 1 ? '' : 's'}',
              style: TextStyle(color: kTextGray, fontSize: 12),
            ),
            onTap: () {
              setState(() => _selectedContact = username);
            },
          );
        },
      ),
    );
  }

  Widget _buildContactDetail(bool isDark, String username) {
    final sharedRoomIds = _contactRooms[username] ?? [];
    final sharedRooms =
        _rooms.where((room) => sharedRoomIds.contains(room['id'])).toList();

    return Scaffold(
      appBar: AppBar(
        flexibleSpace: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: Theme.of(context).brightness == Brightness.dark
                  ? [
                      Colors.black.withOpacity(0.6),
                      Colors.black.withOpacity(0.2),
                    ]
                  : [
                      Colors.white.withOpacity(0.6),
                      Colors.white.withOpacity(0.2),
                    ],
            ),
          ),
        ),
        title: Text(username),
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back),
          onPressed: () {
            setState(() => _selectedContact = null);
          },
        ),
      ),
      body: Column(
        children: [
          SizedBox(height: 20),
          CircleAvatar(
            radius: 50,
            backgroundColor: isDark ? Colors.grey[800] : Colors.grey[300],
            child: Text(
              username[0].toUpperCase(),
              style: TextStyle(
                fontSize: 40,
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : Colors.black,
              ),
            ),
          ),
          SizedBox(height: 16),
          Text(
            username,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              fontFamily: 'Satoshi',
            ),
          ),
          SizedBox(height: 8),
          Text(
            'Shared ${sharedRooms.length} chat room${sharedRooms.length == 1 ? '' : 's'}',
            style: TextStyle(
              fontSize: 14,
              color: kTextGray,
              fontFamily: 'Satoshi',
            ),
          ),
          SizedBox(height: 24),
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Shared Chat Rooms',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: kTextGray,
                  fontFamily: 'Satoshi',
                ),
              ),
            ),
          ),
          SizedBox(height: 8),
          Expanded(
            child: ListView.builder(
              itemCount: sharedRooms.length,
              itemBuilder: (context, index) {
                final room = sharedRooms[index];
                return ListTile(
                  leading: Text('💬', style: TextStyle(fontSize: 20)),
                  title: Text(
                    room['name'],
                    style: TextStyle(fontFamily: 'Satoshi'),
                  ),
                  trailing: Icon(Icons.arrow_forward_ios, size: 16),
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => ChatDetailPage(
                          roomId: room['id'].toString(),
                          roomName: room['name'],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildGradientAppBar(String title) {
    return AppBar(
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
        title,
        style: TextStyle(
          fontFamily: 'Boska',
          fontSize: 28,
          fontWeight: FontWeight.w700,
        ),
      ),
      centerTitle: true,
      backgroundColor: Colors.transparent,
      elevation: 0,
    );
  }
}
