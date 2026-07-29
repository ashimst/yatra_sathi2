import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';

class FeaturedTripCard extends StatelessWidget {
  final String name, subtitle;

  const FeaturedTripCard({
    super.key,
    required this.name,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 200,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFEDF5ED),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              const Icon(Icons.location_on_outlined,
                  size: 16, color: kOrange),
              const SizedBox(width: 4),
            ],
          ),
          const SizedBox(height: 6),
          Text(name,
              style: GoogleFonts.inter(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: kDark)),
          const SizedBox(height: 2),
          Text(subtitle,
              style: GoogleFonts.inter(fontSize: 12, color: kGray)),
        ],
      ),
    );
  }
}