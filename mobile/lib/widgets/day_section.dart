import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/screens/place_detail_screen.dart';

class DaySection extends StatelessWidget {
  final String day;
  final List<Map<String, dynamic>> stops;

  const DaySection({
    super.key,
    required this.day,
    required this.stops,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(day,
            style: GoogleFonts.inter(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: kGray,
                letterSpacing: 0.5)),
        const SizedBox(height: 10),
        Container(
          margin: const EdgeInsets.only(bottom: 20),
          decoration: BoxDecoration(
              color: kCardBg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: kBorder)),
          child: Column(
            children: stops.asMap().entries.map((entry) {
              final i = entry.key;
              final stop = entry.value;
              final hasPlace = stop['place'] != null;
              final Place? place = stop['place'] as Place?;
              final notes = stop['notes'] as String?;
              final String? descText = () {
                if (notes != null && notes.isNotEmpty) return notes;
                if (place != null) {
                  final desc = place.safeDescription;
                  // Skip default generic descriptions like the category fallback
                  if (desc.isNotEmpty && desc.toLowerCase() != place.category.toLowerCase()) {
                    return desc;
                  }
                }
                return null;
              }();

              return Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                    child: Row(
                      crossAxisAlignment:
                          CrossAxisAlignment.start,
                      children: [
                        Column(children: [
                          Text(stop['time']!,
                              style: GoogleFonts.inter(
                                  fontSize: 11,
                                  color: kGray,
                                  fontWeight:
                                      FontWeight.w600)),
                          const SizedBox(height: 4),
                          Container(
                              width: 1,
                              height: descText != null ? 56 : 32,
                              color: kBorder),
                        ]),
                        const SizedBox(width: 14),
                        Expanded(
                            child: Column(
                          crossAxisAlignment:
                              CrossAxisAlignment.start,
                          children: [
                            Text(stop['name']!,
                                style: GoogleFonts.inter(
                                    fontSize: 14,
                                    fontWeight:
                                        FontWeight.w600,
                                    color: kDark)),
                            const SizedBox(height: 2),
                            Text(
                                '${stop['category']} · ${stop['duration']}',
                                style: GoogleFonts.inter(
                                    fontSize: 12,
                                    color: kGray)),
                            if (descText != null) ...[
                              const SizedBox(height: 8),
                              Text(descText,
                                  style: GoogleFonts.inter(
                                      fontSize: 12,
                                      color: kDark
                                          .withValues(alpha: 0.72),
                                      height: 1.35),
                                  maxLines: 4,
                                  overflow: TextOverflow.ellipsis),
                            ],
                          ],
                        )),
                        if (hasPlace) ...[
                          IconButton(
                            icon: const Icon(
                                Icons.info_outline,
                                color: kOrange,
                                size: 18),
                            onPressed: () {
                              Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (_) =>
                                          PlaceDetailScreen(
                                              place:
                                                  stop['place']
                                                      as Place)));
                            },
                          ),
                        ]
                      ],
                    ),
                  ),
                  if (i < stops.length - 1)
                    const Divider(height: 1, color: kBorder),
                ],
              );
            }).toList(),
          ),
        ),
      ],
    );
  }
}