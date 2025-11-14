import 'package:flutter/material.dart';
import 'dart:ui';
import '../services/api_client.dart';
import '../providers/auth_provider.dart';
import '../themes/colors.dart';
import 'chat_detail_page.dart';
import 'contacts_page.dart';
import 'profile_page.dart';
import 'package:provider/provider.dart';

class WebShell extends StatefulWidget {
  const WebShell();

  @override
  State<WebShell> createState() => _WebShellState();
}

class _WebShellState extends State<WebShell> {
  int _currentTab = 0; // 0: Chats, 1: Contacts, 2: Profile
  List<Map<String, dynamic>> _rooms = [];
  bool _isLoadingRooms = true;
  String? _selectedRoomId;

  @override
  void initState() {
    super.initState();
    _loadRooms();
  }

  Future<void> _loadRooms() async {
    try {
      final authProvider = context.read<AuthProvider>();
      if (authProvider.token != null) {
        apiClient.token = authProvider.token;
      }

      final rooms = await apiClient.getRooms();
      setState(() {
        _rooms = rooms
            .map((r) => {
                  'id': r['id'] as int,
                  'name': r['name'] as String,
                })
            .toList();
        _isLoadingRooms = false;
        // Select first room by default
        if (_rooms.isNotEmpty && _selectedRoomId == null) {
          _selectedRoomId = _rooms[0]['id'].toString();
        }
      });
    } catch (e) {
      print('Error loading rooms: $e');
      setState(() => _isLoadingRooms = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Grocery AI',
          style: TextStyle(
            fontFamily: 'Boska',
            fontSize: 24,
            fontWeight: FontWeight.w700,
          ),
        ),
        centerTitle: false,
        backgroundColor: isDark ? Colors.grey[900] : Colors.white,
        elevation: 1,
        actions: [
          _buildNavButton(
            icon: Icons.home,
            label: 'Chats',
            isActive: _currentTab == 0,
            onPressed: () => setState(() => _currentTab = 0),
          ),
          _buildNavButton(
            icon: Icons.people,
            label: 'Contacts',
            isActive: _currentTab == 1,
            onPressed: () => setState(() => _currentTab = 1),
          ),
          _buildNavButton(
            icon: Icons.person,
            label: 'Profile',
            isActive: _currentTab == 2,
            onPressed: () => setState(() => _currentTab = 2),
          ),
          SizedBox(width: 16),
        ],
      ),
      body: _currentTab == 0
          ? _buildChatLayout(isDark)
          : _currentTab == 1
              ? ContactsPage()
              : ProfilePage(),
    );
  }

  Widget _buildChatLayout(bool isDark) {
    return Row(
      children: [
        // Left Sidebar - Chat Room List
        Container(
          width: 300,
          decoration: BoxDecoration(
            border: Border(
              right: BorderSide(
                color: isDark ? Colors.grey[800]! : Colors.grey[300]!,
                width: 1,
              ),
            ),
          ),
          child: _isLoadingRooms
              ? Center(child: CircularProgressIndicator())
              : _rooms.isEmpty
                  ? Center(
                      child: Text(
                        'No chat rooms yet',
                        style:
                            TextStyle(color: kTextGray, fontFamily: 'Satoshi'),
                      ),
                    )
                  : ListView.builder(
                      itemCount: _rooms.length,
                      itemBuilder: (context, index) {
                        final room = _rooms[index];
                        final roomId = room['id'].toString();
                        final isSelected = _selectedRoomId == roomId;

                        return Container(
                          decoration: BoxDecoration(
                            color: isSelected
                                ? (isDark ? Colors.grey[800] : Colors.grey[200])
                                : Colors.transparent,
                          ),
                          child: ListTile(
                            selected: isSelected,
                            title: Text(
                              room['name'],
                              style: TextStyle(
                                fontFamily: 'Satoshi',
                                fontWeight: isSelected
                                    ? FontWeight.w700
                                    : FontWeight.w400,
                              ),
                            ),
                            onTap: () {
                              setState(() => _selectedRoomId = roomId);
                            },
                          ),
                        );
                      },
                    ),
        ),

        // Right Side - Chat Content
        Expanded(
          child: _selectedRoomId != null
              ? ChatDetailPage(
                  roomId: _selectedRoomId!,
                  roomName: _rooms.firstWhere(
                      (r) => r['id'].toString() == _selectedRoomId)['name'],
                )
              : Center(
                  child: Text(
                    'Select a chat room',
                    style: TextStyle(color: kTextGray, fontFamily: 'Satoshi'),
                  ),
                ),
        ),
      ],
    );
  }

  Widget _buildNavButton({
    required IconData icon,
    required String label,
    required bool isActive,
    required VoidCallback onPressed,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Padding(
      padding: EdgeInsets.symmetric(horizontal: 8),
      child: GestureDetector(
        onTap: onPressed,
        child: Container(
          padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: isActive
                ? (isDark
                    ? Colors.cyan.withValues(alpha: 0.1)
                    : Colors.blue.withValues(alpha: 0.1))
                : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 20,
                color: isActive
                    ? (isDark ? Colors.cyan : Colors.blue)
                    : (isDark ? Colors.white70 : Colors.black54),
              ),
              SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  fontSize: 14,
                  color: isActive
                      ? (isDark ? Colors.cyan : Colors.blue)
                      : (isDark ? Colors.white70 : Colors.black54),
                  fontFamily: 'Satoshi',
                  fontWeight: isActive ? FontWeight.bold : FontWeight.w400,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
