import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';

class WeatherCard extends StatelessWidget {
  final String city;
  final int temp;
  final String desc;
  final bool isLoading;

  const WeatherCard({
    super.key,
    required this.city,
    required this.temp,
    required this.desc,
    required this.isLoading,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFD6EAF5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kBorder),
      ),
      child: isLoading
          ? const Center(
              child: CircularProgressIndicator(
                  strokeWidth: 2, color: Color(0xFF4A8FA8)))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Row(
                  children: [
                    const Icon(Icons.cloud_outlined,
                        size: 16, color: Color(0xFF4A8FA8)),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        city,
                        style: GoogleFonts.inter(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.8,
                            color: const Color(0xFF4A8FA8)),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text('$temp°C',
                    style: GoogleFonts.playfairDisplay(
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        color: kDark)),
                Text(desc,
                    style: GoogleFonts.inter(
                        fontSize: 10, color: kGray),
                    overflow: TextOverflow.ellipsis),
              ],
            ),
    );
  }
}