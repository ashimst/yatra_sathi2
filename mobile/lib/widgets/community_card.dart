import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/created_itinerary.dart';
import 'package:mobile/widgets/placeholder_image.dart';
import 'package:mobile/screens/public_itinerary_detail_screen.dart';

class CommunityCard extends StatelessWidget {
  final CreatedItinerary itinerary;
  final VoidCallback onUpdate;

  const CommunityCard({
    super.key,
    required this.itinerary,
    required this.onUpdate,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 5),
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: kBorder),
      ),
      child: Row(
        children: [
          ClipRRect(
            borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(15),
                bottomLeft: Radius.circular(15)),
            child: buildPlaceholderImage('temple',
                width: 90, height: 90),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(itinerary.title,
                      style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: kDark)),
                  const SizedBox(height: 2),
                  Text(
                      '${itinerary.author} · ${itinerary.travelers} traveler(s)',
                      style: GoogleFonts.inter(
                          fontSize: 12, color: kGray)),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      _chip('${itinerary.days} days'),
                      const SizedBox(width: 6),
                      _chip(itinerary.budget),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      GestureDetector(
                        onTap: () {
                          itinerary.likes++;
                          onUpdate();
                        },
                        child: Row(
                          children: [
                            const Icon(Icons.favorite,
                                size: 14, color: kOrange),
                            const SizedBox(width: 3),
                            Text('${itinerary.likes}',
                                style: GoogleFonts.inter(
                                    fontSize: 12, color: kGray)),
                          ],
                        ),
                      ),
                      const SizedBox(width: 15),
                      GestureDetector(
                        onTap: () {
                          Navigator.push(
                              context,
                              MaterialPageRoute(
                                  builder: (_) =>
                                      PublicItineraryDetailScreen(
                                          itinerary:
                                              itinerary)));
                        },
                        child: Row(
                          children: [
                            const Icon(Icons.edit,
                                size: 14, color: kGray),
                            const SizedBox(width: 3),
                            Text('View & Edit',
                                style: GoogleFonts.inter(
                                    fontSize: 12,
                                    color: kOrange,
                                    fontWeight: FontWeight.w600)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _chip(String label) => Container(
        padding:
            const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: kCream,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: kBorder),
        ),
        child: Text(label,
            style: GoogleFonts.inter(
                fontSize: 11,
                color: kGray,
                fontWeight: FontWeight.w500)),
      );
}