import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'pages/login_page.dart';
import 'pages/main_shell.dart';
import 'pages/web_shell.dart';
import 'themes/light_mode.dart';
import 'themes/dark_mode.dart';
import 'providers/theme_provider.dart';
import 'providers/auth_provider.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp();

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        ChangeNotifierProvider(create: (_) => AuthProvider()),
      ],
      child: Consumer<ThemeProvider>(
        builder: (context, themeProvider, _) {
          return MaterialApp(
            title: 'Grocery AI',
            theme: lightTheme,
            darkTheme: darkTheme,
            themeMode: themeProvider.themeMode,
            home: Consumer<AuthProvider>(
              builder: (context, authProvider, _) {
                // Show loading screen while checking auth status
                if (authProvider.isLoading) {
                  return Scaffold(
                    body: Center(
                      child: CircularProgressIndicator(),
                    ),
                  );
                }

                // If logged in, go to home page, otherwise go to login page
                if (!authProvider.isLoggedIn) {
                  return LoginPage();
                }

                // Use different shell based on screen size
                return LayoutBuilder(
                  builder: (context, constraints) {
                    // Use web shell if screen width > 800 (web/tablet)
                    if (constraints.maxWidth > 800) {
                      return WebShell();
                    }
                    // Use mobile shell for smaller screens
                    return MainShell();
                  },
                );
              },
            ),
            debugShowCheckedModeBanner: false,
          );
        },
      ),
    );
  }
}
