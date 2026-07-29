import 'package:flutter/material.dart';

Widget buildPlaceholderImage(String category,
    {double width = 56, double height = 56}) {
  Color bg;
  Color iconColor;
  IconData icon;
  switch (category.toLowerCase()) {
    case 'hindu temple':
    case 'buddhist temple':
      bg = const Color(0xFFFFE8D6);
      iconColor = const Color(0xFFCC8855);
      icon = Icons.temple_hindu;
      break;
    case 'mountain range':
    case 'mountain peak':
    case 'hiking area':
      bg = const Color(0xFFD6EAF5);
      iconColor = const Color(0xFF4A8FA8);
      icon = Icons.terrain;
      break;
    case 'museum':
      bg = const Color(0xFFE8D6F5);
      iconColor = const Color(0xFF7B1FA2);
      icon = Icons.account_balance;
      break;
    case 'wildlife':
      bg = const Color(0xFFD6F5D6);
      iconColor = const Color(0xFF388E3C);
      icon = Icons.pets;
      break;
    default:
      bg = const Color(0xFFE8F5D6);
      iconColor = const Color(0xFF558B2F);
      icon = Icons.landscape;
  }
  return Container(
    width: width,
    height: height,
    color: bg,
    child: Icon(icon, color: iconColor, size: width * 0.5),
  );
}