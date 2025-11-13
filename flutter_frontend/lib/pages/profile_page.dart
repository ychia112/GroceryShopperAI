import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../themes/colors.dart';
import '../themes/dark_mode.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/image_service.dart';
import '../services/storage_service.dart';
import '../providers/theme_provider.dart';
import '../providers/auth_provider.dart';
import 'login_page.dart';

class ProfilePage extends StatefulWidget {
  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  late String _currentUsername;
  bool _isLoading = true;
  String _currentLLMModel = 'gemini';
  List<String> _availableLLMModels = ['gemini', 'openai'];

  @override
  void initState() {
    super.initState();
    _initUsername();
  }

  Future<void> _initUsername() async {
    try {
      final storageService = getStorageService();
      final token = await storageService.read(key: 'auth_token');
      if (token != null) {
        _currentUsername = getUsernameFromToken(token) ?? 'User';
        try {
          final result = await apiClient.getLLMModel();
          if (result['available_models'] != null) {
            _availableLLMModels = List<String>.from(result['available_models']);
          }
          _currentLLMModel = result['model'] ?? 'gemini';
        } catch (e) {
          print('Error loading LLM model: $e');
          _currentLLMModel = 'gemini';
        }
      } else {
        _currentUsername = 'User';
        setState(() => _isLoading = false);
        return;
      }
    } catch (e) {
      print('Error loading username: $e');
    }
    setState(() => _isLoading = false);
  }

  Future<void> _logout() async {
    try {
      // Clear token from AuthProvider
      final authProvider = context.read<AuthProvider>();
      await authProvider.logout();

      if (mounted) {
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder: (_) => LoginPage()),
          (route) => false,
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Logout failed: $e')),
      );
    }
  }

  Future<void> _showLLMModelDialog() async {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          'Select AI Model',
          style: TextStyle(fontFamily: 'Satoshi', fontWeight: FontWeight.w700),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: _availableLLMModels.map((model) {
            final isSelected = model == _currentLLMModel;

            return GestureDetector(
              onTap: () async {
                try {
                  await apiClient.updateLLMModel(model);
                  setState(() => _currentLLMModel = model);
                  if (mounted) {
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                          content: Text(
                              'AI Model changed to ${model.toUpperCase()}')),
                    );
                  }
                } catch (e) {
                  print('Error updating LLM model: $e');
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Failed to update model: $e')),
                    );
                  }
                }
              },
              child: Container(
                margin: EdgeInsets.symmetric(vertical: 8),
                padding: EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: isSelected
                      ? kSecondary.withOpacity(0.2)
                      : Colors.grey[100],
                  border: Border.all(
                    color: isSelected ? kSecondary : Colors.grey[300]!,
                    width: 2,
                  ),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      isSelected ? Icons.check_circle : Icons.circle_outlined,
                      color: isSelected ? kSecondary : kTextGray,
                    ),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        model.toUpperCase(),
                        style: TextStyle(
                          fontFamily: 'Satoshi',
                          fontWeight:
                              isSelected ? FontWeight.w700 : FontWeight.w400,
                          color: kTextDark,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel', style: TextStyle(fontFamily: 'Satoshi')),
          ),
        ],
      ),
    );
  }

  Future<void> _changeAvatar() async {
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

        // TODO: backend API to upload avatar
        // final base64Image = await ImageService.imageToBase64(imageFile);
        // await apiClient.updateUserAvatar(base64Image);

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Avatar updated successfully')),
          );
        }
      }
    } catch (e) {
      print('Error changing avatar: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to change avatar: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
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
          'Profile',
          style: TextStyle(
            fontFamily: 'Boska',
            fontSize: 28,
            fontWeight: FontWeight.w700,
            color: Theme.of(context).appBarTheme.titleTextStyle?.color,
          ),
        ),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: EdgeInsets.all(20),
              child: Column(
                children: [
                  // Avatar with Edit Button
                  Stack(
                    children: [
                      Container(
                        width: 100,
                        height: 100,
                        decoration: BoxDecoration(
                          color: Theme.of(context).brightness == Brightness.dark
                              ? kDarkCard
                              : kPrimary,
                          shape: BoxShape.circle,
                        ),
                        child: Center(
                          child: Text(
                            (_currentUsername.isNotEmpty
                                ? _currentUsername[0].toUpperCase()
                                : '?'),
                            style: TextStyle(
                              fontFamily: 'Boska',
                              fontSize: 48,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                      // Edit Button at Bottom Right
                      Positioned(
                        bottom: 0,
                        right: 0,
                        child: GestureDetector(
                          onTap: _changeAvatar,
                          child: Container(
                            width: 36,
                            height: 36,
                            decoration: BoxDecoration(
                              color: kSecondary,
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: Colors.white,
                                width: 2,
                              ),
                            ),
                            child: Icon(
                              Icons.edit,
                              color: Colors.white,
                              size: 18,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 20),

                  // Username
                  Text(
                    _currentUsername,
                    style: TextStyle(
                      fontFamily: 'Boska',
                      fontSize: 24,
                      fontWeight: FontWeight.w700,
                      color: kTextDark,
                    ),
                  ),
                  SizedBox(height: 30),

                  // Settings Section
                  Consumer<ThemeProvider>(
                    builder: (context, themeProvider, _) {
                      final isDarkMode =
                          Theme.of(context).brightness == Brightness.dark;
                      return Container(
                        margin: EdgeInsets.only(bottom: 12),
                        decoration: BoxDecoration(
                          color:
                              isDarkMode ? Color(0xFF0D3D2E) : Colors.grey[100],
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: isDarkMode
                                ? Color(0xFF1A5C47)
                                : Colors.grey[300]!,
                          ),
                        ),
                        child: ListTile(
                          leading: Icon(
                            Icons.brightness_6,
                            color: isDarkMode ? kDarkText : kPrimary,
                          ),
                          title: Text(
                            'Theme',
                            style: TextStyle(
                              fontFamily: 'Satoshi',
                              fontWeight: FontWeight.w400,
                              color: isDarkMode ? kDarkText : kTextDark,
                            ),
                          ),
                          subtitle: Text(
                            themeProvider.isDarkMode
                                ? 'Dark Mode'
                                : 'Light Mode',
                            style: TextStyle(
                              fontFamily: 'Satoshi',
                              color:
                                  isDarkMode ? kDarkTextSecondary : kTextGray,
                            ),
                          ),
                          trailing: Switch(
                            value: themeProvider.isDarkMode,
                            onChanged: (value) {
                              themeProvider.setThemeMode(
                                value ? ThemeMode.dark : ThemeMode.light,
                              );
                            },
                            activeColor: kSecondary,
                            inactiveThumbColor:
                                const Color.fromARGB(255, 148, 171, 149),
                          ),
                        ),
                      );
                    },
                  ),
                  _buildSettingTile(
                    context: context,
                    icon: Icons.smart_toy,
                    title: 'AI Model',
                    subtitle: _currentLLMModel.toUpperCase(),
                    onTap: _showLLMModelDialog,
                  ),
                  _buildSettingTile(
                    context: context,
                    icon: Icons.language,
                    title: 'Language',
                    subtitle: 'English',
                    onTap: () {},
                  ),
                  SizedBox(height: 30),

                  // Logout Button
                  SizedBox(
                    width: double.infinity,
                    child: Consumer<ThemeProvider>(
                      builder: (context, themeProvider, _) {
                        final isLight =
                            themeProvider.themeMode == ThemeMode.light;
                        return ElevatedButton(
                          onPressed: _logout,
                          style: ElevatedButton.styleFrom(
                            backgroundColor:
                                isLight ? Colors.red : Color(0xFFB83C3C),
                            padding: EdgeInsets.symmetric(vertical: 12),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          child: Text(
                            'Logout',
                            style: TextStyle(
                              fontFamily: 'Satoshi',
                              fontSize: 16,
                              fontWeight: FontWeight.w400,
                              color: Colors.white,
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildSettingTile({
    required BuildContext context,
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    return Container(
      margin: EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: isDarkMode ? Color(0xFF0D3D2E) : Colors.grey[100],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isDarkMode ? Color(0xFF1A5C47) : Colors.grey[300]!,
        ),
      ),
      child: ListTile(
        leading: Icon(icon, color: isDarkMode ? kDarkText : kPrimary),
        title: Text(
          title,
          style: TextStyle(
            fontFamily: 'Satoshi',
            fontWeight: FontWeight.w400,
            color: isDarkMode ? kDarkText : kTextDark,
          ),
        ),
        subtitle: Text(
          subtitle,
          style: TextStyle(
            fontFamily: 'Satoshi',
            color: isDarkMode ? kDarkTextSecondary : kTextGray,
          ),
        ),
        trailing: Icon(
          Icons.chevron_right,
          color: isDarkMode ? kDarkTextSecondary : kTextGray,
        ),
        onTap: onTap,
      ),
    );
  }
}
