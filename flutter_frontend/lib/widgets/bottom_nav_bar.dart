import 'package:flutter/material.dart';
import 'dart:ui';

class BottomNavBar extends StatelessWidget {
  final Function()? onSearchPressed;
  final Function()? onCreatePressed;
  final Function()? onHomePressed;
  final Function()? onContactsPressed;
  final Function()? onProfilePressed;

  const BottomNavBar({
    this.onSearchPressed,
    this.onCreatePressed,
    this.onHomePressed,
    this.onContactsPressed,
    this.onProfilePressed,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Positioned(
      bottom: 20,
      left: 16,
      right: 16,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(50),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 15.0, sigmaY: 15.0),
          child: Container(
            decoration: BoxDecoration(
              color: isDark
                  ? Colors.black.withValues(alpha: 0.3)
                  : Colors.white.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(50),
              border: Border.all(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.2)
                    : Colors.white.withValues(alpha: 0.4),
                width: 1.5,
              ),
            ),
            child: Padding(
              padding: EdgeInsets.symmetric(vertical: 8, horizontal: 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildNavButton(
                    icon: Icons.search,
                    label: 'Search',
                    onPressed: onSearchPressed,
                    isDark: isDark,
                  ),
                  _buildNavButton(
                    icon: Icons.add,
                    label: 'Create',
                    onPressed: onCreatePressed,
                    isDark: isDark,
                  ),
                  _buildNavButton(
                    icon: Icons.home,
                    label: 'Home',
                    onPressed: onHomePressed,
                    isDark: isDark,
                  ),
                  _buildNavButton(
                    icon: Icons.people,
                    label: 'Contacts',
                    onPressed: onContactsPressed,
                    isDark: isDark,
                  ),
                  _buildNavButton(
                    icon: Icons.person,
                    label: 'Profile',
                    onPressed: onProfilePressed,
                    isDark: isDark,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildNavButton({
    required IconData icon,
    required String label,
    required Function()? onPressed,
    required bool isDark,
  }) {
    return GestureDetector(
      onTap: onPressed,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 20,
            color: isDark ? Colors.white : Colors.black87,
          ),
          SizedBox(height: 2),
          Text(
            label,
            style: TextStyle(
              fontSize: 8,
              color: isDark ? Colors.white : Colors.black87,
              fontFamily: 'Satoshi',
            ),
          ),
        ],
      ),
    );
  }
}
