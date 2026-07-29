import 'package:flutter/foundation.dart'; // <-- REQUIRED
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ─────────────────────────────────────────────────────────────────
// COLORS & THEME
// ─────────────────────────────────────────────────────────────────

const Color kCream = Color(0xFFF5F0E8);
const Color kOrange = Color(0xFFCC5200);
const Color kOrangeLight = Color(0xFFE87340);
const Color kDark = Color(0xFF1A1A1A);
const Color kGray = Color(0xFF6B6B6B);
const Color kCardBg = Colors.white;
const Color kBorder = Color(0xFFE0DAD0);

// ─────────────────────────────────────────────────────────────────
// API KEYS & URLs
// ─────────────────────────────────────────────────────────────────

const String kOpenWeatherApiKey =
    '8424a1b023fdfb82ee202163b27bcfb9';

String get kBaseUrl {
  if (kIsWeb) {
    return 'http://localhost:8000'; //https://sh8sghtw-8000.inc1.devtunnels.ms:8000
  }

  switch (defaultTargetPlatform) {
    case TargetPlatform.android:
      return 'http://10.0.2.2:8000';
    case TargetPlatform.iOS:
    case TargetPlatform.macOS:
    case TargetPlatform.windows:
    case TargetPlatform.linux:
    case TargetPlatform.fuchsia:
      return 'http://localhost:8000';
  }
}

// ─────────────────────────────────────────────────────────────────
// THEME
// ─────────────────────────────────────────────────────────────────

ThemeData yatraSathiTheme() {
  return ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: kCream,
    colorScheme: const ColorScheme.light(
      primary: kOrange,
      secondary: kOrangeLight,
      surface: kCream,
      onPrimary: Colors.white,
      onSurface: kDark,
    ),

    textTheme: GoogleFonts.interTextTheme().copyWith(
      displayLarge: GoogleFonts.playfairDisplay(
        fontSize: 36,
        fontWeight: FontWeight.w700,
        fontStyle: FontStyle.italic,
        color: kDark,
      ),
      displayMedium: GoogleFonts.playfairDisplay(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        fontStyle: FontStyle.italic,
        color: kDark,
      ),
      headlineMedium: GoogleFonts.playfairDisplay(
        fontSize: 22,
        fontWeight: FontWeight.w600,
        color: kDark,
      ),
      titleLarge: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: kDark,
      ),
      titleMedium: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w500,
        color: kDark,
      ),
      bodyLarge: GoogleFonts.inter(
        fontSize: 14,
        color: kDark,
      ),
      bodyMedium: GoogleFonts.inter(
        fontSize: 13,
        color: kGray,
      ),
      labelLarge: GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.8,
        color: kGray,
      ),
    ),

    cardTheme: const CardThemeData(
      color: kCardBg,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(16)),
        side: BorderSide(
          color: kBorder,
          width: 1,
        ),
      ),
    ),

    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: 16,
        vertical: 14,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: kBorder),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: kBorder),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(
          color: kOrange,
          width: 1.5,
        ),
      ),
    ),

    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: kOrange,
        foregroundColor: Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(
          horizontal: 24,
          vertical: 14,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        textStyle: GoogleFonts.inter(
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
    ),
  );
}