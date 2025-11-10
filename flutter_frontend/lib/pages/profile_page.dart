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
  String _currentLLMModel = 'tinyllama';
  List<String> _availableLLMModels = ['tinyllama', 'openai'];
  bool _tinyllamaAvailable = false;

  // 下載進度追蹤
  int _downloadProgress = 0;
  String _downloadStatus = 'idle'; // idle, downloading, completed, failed
  String _downloadMessage = '';
  bool _isDownloading = false;

  @override
  void initState() {
    super.initState();
    _initUsername();
  }

  Future<void> _initUsername() async {
    try {
      final storageService = getStorageService();
      final token = await storageService.read(key: 'token');
      if (token != null) {
        _currentUsername = getUsernameFromToken(token) ?? 'User';
        // 加載用戶的 LLM 模型偏好和可用模型
        try {
          final result = await apiClient.getLLMModel();
          if (result['available_models'] != null) {
            _availableLLMModels = List<String>.from(result['available_models']);
          }
          _currentLLMModel = result['model'] ?? 'tinyllama';
          _tinyllamaAvailable = result['tinyllama_available'] ?? false;
        } catch (e) {
          print('Error loading LLM model: $e');
          _currentLLMModel = 'tinyllama';
          _tinyllamaAvailable = false;
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

  Future<void> _downloadTinyLlama() async {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          'Download TinyLlama',
          style: TextStyle(fontFamily: 'Boska', fontWeight: FontWeight.w700),
        ),
        content: Text(
          'TinyLlama will be downloaded and installed locally using Ollama.\n\nThis may take a few minutes.',
          style: TextStyle(fontFamily: 'Boska'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel', style: TextStyle(fontFamily: 'Boska')),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(context);

              // 顯示進度對話框
              showDialog(
                context: context,
                barrierDismissible: true,
                builder: (context) => StatefulBuilder(
                  builder: (context, setState) {
                    // 啟動進度輪詢
                    _startProgressPolling(setState);

                    return AlertDialog(
                      title: Text(
                        'Downloading TinyLlama...',
                        style: TextStyle(
                            fontFamily: 'Boska', fontWeight: FontWeight.w700),
                      ),
                      content: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // 進度條
                          ClipRRect(
                            borderRadius: BorderRadius.circular(10),
                            child: LinearProgressIndicator(
                              value: _downloadProgress / 100.0,
                              minHeight: 8,
                              backgroundColor: Colors.grey[300],
                              valueColor:
                                  AlwaysStoppedAnimation<Color>(kSecondary),
                            ),
                          ),
                          SizedBox(height: 12),

                          // 進度百分比
                          Text(
                            '${_downloadProgress}%',
                            style: TextStyle(
                              fontFamily: 'Boska',
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          SizedBox(height: 12),

                          // 下載訊息
                          Text(
                            _downloadMessage.isNotEmpty
                                ? _downloadMessage
                                : 'Initializing download...',
                            style: TextStyle(
                              fontFamily: 'Boska',
                              fontSize: 12,
                              color: Colors.grey[700],
                            ),
                            textAlign: TextAlign.center,
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                      actions: [
                        if (_downloadStatus == 'completed')
                          ElevatedButton(
                            onPressed: () => Navigator.pop(context),
                            style: ElevatedButton.styleFrom(
                                backgroundColor: kSecondary),
                            child: Text('Done',
                                style: TextStyle(
                                    fontFamily: 'Boska', color: Colors.white)),
                          )
                        else if (_downloadStatus == 'failed')
                          Column(
                            children: [
                              ElevatedButton(
                                onPressed: () => Navigator.pop(context),
                                style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.red),
                                child: Text('Close',
                                    style: TextStyle(
                                        fontFamily: 'Boska',
                                        color: Colors.white)),
                              ),
                            ],
                          )
                        else
                          TextButton(
                            onPressed: () => Navigator.pop(context),
                            child: Text('Close',
                                style: TextStyle(fontFamily: 'Boska')),
                          ),
                      ],
                    );
                  },
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: kSecondary,
            ),
            child: Text(
              'Download',
              style: TextStyle(fontFamily: 'Boska', color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }

  void _startProgressPolling(StateSetter setState) {
    _isDownloading = true;
    _downloadProgress = 0;
    _downloadStatus = 'downloading';
    _downloadMessage = 'Starting download...';

    Future(() async {
      try {
        // 發起下載
        await apiClient.downloadTinyLlama();

        // 定時輪詢進度
        int attempts = 0;
        int maxAttempts = 300; // 5 分鐘最多輪詢

        while (_isDownloading && attempts < maxAttempts) {
          attempts++;
          await Future.delayed(Duration(milliseconds: 500));

          try {
            final progress = await apiClient.getDownloadProgress();

            if (mounted) {
              setState(() {
                _downloadProgress =
                    (progress['progress'] as num?)?.toInt() ?? 0;
                _downloadStatus = progress['status'] ?? 'downloading';
                _downloadMessage = progress['message'] ?? '';
              });
            }

            // 下載完成或失敗
            if (_downloadStatus == 'completed' || _downloadStatus == 'failed') {
              _isDownloading = false;

              if (_downloadStatus == 'completed') {
                // 刷新模型可用性
                if (mounted) {
                  try {
                    final result = await apiClient.getLLMModel();
                    setState(() {
                      _tinyllamaAvailable =
                          result['tinyllama_available'] ?? false;
                    });
                  } catch (e) {
                    print('Error refreshing LLM model: $e');
                  }
                }
              }

              break;
            }
          } catch (e) {
            print('Error polling download progress: $e');
          }
        }

        if (attempts >= maxAttempts && _downloadStatus != 'completed') {
          setState(() {
            _downloadStatus = 'failed';
            _downloadMessage = 'Download timeout';
          });
          _isDownloading = false;
        }
      } catch (e) {
        print('Error in download task: $e');
        if (mounted) {
          setState(() {
            _downloadStatus = 'failed';
            _downloadMessage = 'Error: $e';
          });
        }
        _isDownloading = false;
      }
    });
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

  Future<void> _showThemeDialog(
      BuildContext context, ThemeProvider themeProvider) async {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          'Select Theme',
          style: TextStyle(fontFamily: 'Boska', fontWeight: FontWeight.w700),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            GestureDetector(
              onTap: () {
                themeProvider.setThemeMode(ThemeMode.light);
                Navigator.pop(context);
              },
              child: Container(
                padding: EdgeInsets.all(12),
                margin: EdgeInsets.only(bottom: 8),
                decoration: BoxDecoration(
                  border: Border.all(
                    color: themeProvider.themeMode == ThemeMode.light
                        ? kPrimary
                        : Colors.grey,
                    width: 2,
                  ),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.light_mode,
                      color: themeProvider.themeMode == ThemeMode.light
                          ? kPrimary
                          : Colors.grey,
                      size: 24,
                    ),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Light Mode',
                        style: TextStyle(
                          fontFamily: 'Boska',
                          fontWeight: themeProvider.themeMode == ThemeMode.light
                              ? FontWeight.w700
                              : FontWeight.w400,
                          color: themeProvider.themeMode == ThemeMode.light
                              ? kPrimary
                              : Colors.grey,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            GestureDetector(
              onTap: () {
                themeProvider.setThemeMode(ThemeMode.dark);
                Navigator.pop(context);
              },
              child: Container(
                padding: EdgeInsets.all(12),
                margin: EdgeInsets.only(bottom: 8),
                decoration: BoxDecoration(
                  border: Border.all(
                    color: themeProvider.themeMode == ThemeMode.dark
                        ? kDarkText
                        : Colors.grey,
                    width: 2,
                  ),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.dark_mode,
                      color: themeProvider.themeMode == ThemeMode.dark
                          ? kDarkText
                          : Colors.grey,
                      size: 24,
                    ),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Dark Mode',
                        style: TextStyle(
                          fontFamily: 'Boska',
                          fontWeight: themeProvider.themeMode == ThemeMode.dark
                              ? FontWeight.w700
                              : FontWeight.w400,
                          color: themeProvider.themeMode == ThemeMode.dark
                              ? kDarkText
                              : Colors.grey,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel', style: TextStyle(fontFamily: 'Boska')),
          ),
        ],
      ),
    );
  }

  Future<void> _showLLMModelDialog() async {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          'Select AI Model',
          style: TextStyle(fontFamily: 'Boska', fontWeight: FontWeight.w700),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: _availableLLMModels.map((model) {
            final isSelected = model == _currentLLMModel;
            final isNotAvailable = model == 'tinyllama' && !_tinyllamaAvailable;

            return GestureDetector(
              onTap: isNotAvailable
                  ? null
                  : () async {
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
                            SnackBar(
                                content: Text('Failed to update model: $e')),
                          );
                        }
                      }
                    },
              child: Container(
                margin: EdgeInsets.symmetric(vertical: 8),
                padding: EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: isNotAvailable
                      ? Colors.grey[200]
                      : (isSelected
                          ? kSecondary.withOpacity(0.2)
                          : Colors.grey[100]),
                  border: Border.all(
                    color: isNotAvailable
                        ? Colors.grey[400]!
                        : (isSelected ? kSecondary : Colors.grey[300]!),
                    width: 2,
                  ),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          isSelected
                              ? Icons.check_circle
                              : Icons.circle_outlined,
                          color: isNotAvailable
                              ? Colors.grey[400]
                              : (isSelected ? kSecondary : kTextGray),
                        ),
                        SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            model.toUpperCase(),
                            style: TextStyle(
                              fontFamily: 'Boska',
                              fontWeight: isSelected
                                  ? FontWeight.w700
                                  : FontWeight.w400,
                              color:
                                  isNotAvailable ? Colors.grey[600] : kTextDark,
                            ),
                          ),
                        ),
                      ],
                    ),
                    if (isNotAvailable)
                      Padding(
                        padding: EdgeInsets.only(top: 8, left: 36),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Not installed. ',
                              style: TextStyle(
                                fontFamily: 'Boska',
                                fontSize: 11,
                                color: Colors.red[700],
                              ),
                            ),
                            SizedBox(height: 4),
                            GestureDetector(
                              onTap: _downloadTinyLlama,
                              child: Container(
                                padding: EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: kSecondary.withOpacity(0.2),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  '📥 Download Now',
                                  style: TextStyle(
                                    fontFamily: 'Boska',
                                    fontSize: 11,
                                    color: kSecondary,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                            ),
                          ],
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
            child: Text('Cancel', style: TextStyle(fontFamily: 'Boska')),
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
        title: Text(
          'Profile',
          style: TextStyle(
            fontFamily: 'Boska',
            fontSize: 24,
            fontWeight: FontWeight.w700,
            color: Theme.of(context).appBarTheme.titleTextStyle?.color,
          ),
        ),
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
                            (_currentUsername.isNotEmpty ? _currentUsername[0].toUpperCase() : '?'),
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
                      return _buildSettingTile(
                        context: context,
                        icon: Icons.brightness_6,
                        title: 'Theme',
                        subtitle: themeProvider.isDarkMode
                            ? 'Dark Mode'
                            : 'Light Mode',
                        onTap: () => _showThemeDialog(context, themeProvider),
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
                              fontFamily: 'Boska',
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
            fontFamily: 'Boska',
            fontWeight: FontWeight.w400,
            color: isDarkMode ? kDarkText : kTextDark,
          ),
        ),
        subtitle: Text(
          subtitle,
          style: TextStyle(
            fontFamily: 'Boska',
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
