import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/widgets/placeholder_image.dart';
import 'package:mobile/screens/map_screen.dart';

class PlaceDetailScreen extends StatelessWidget {
  final Place place;
  const PlaceDetailScreen({super.key, required this.place});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kCream,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 280,
            pinned: true,
            backgroundColor: kOrange,
            leading: IconButton(
              icon: Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius:
                        BorderRadius.circular(8)),
                child: const Icon(Icons.arrow_back,
                    color: kDark, size: 18),
              ),
              onPressed: () => Navigator.pop(context),
            ),
            flexibleSpace: FlexibleSpaceBar(
              background: place.imageUrl.isNotEmpty
                  ? Image.network(place.imageUrl,
                      fit: BoxFit.cover,
                      errorBuilder: (c, e, s) =>
                          buildPlaceholderImage(
                              place.category,
                              width: 400,
                              height: 280))
                  : buildPlaceholderImage(
                      place.category,
                      width: 400,
                      height: 280),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment:
                    CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(place.name,
                            style: Theme.of(context)
                                .textTheme
                                .headlineMedium
                                ?.copyWith(
                                    fontStyle:
                                        FontStyle
                                            .italic)),
                      ),
                      Container(
                        padding:
                            const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 6),
                        decoration: BoxDecoration(
                          color: kOrange
                              .withValues(alpha: 0.1),
                          borderRadius:
                              BorderRadius.circular(
                                  20),
                        ),
                        child: Row(children: [
                          const Icon(Icons.star,
                              size: 16,
                              color: kOrange),
                          const SizedBox(width: 4),
                          Text(
                              place.safeRating.toStringAsFixed(1),
                              style: GoogleFonts.inter(
                                  fontWeight:
                                      FontWeight.w700,
                                  color: kOrange)),
                        ]),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                      '${place.category} · ${place.safeDistrict}, ${place.safeProvince}',
                      style: GoogleFonts.inter(
                          fontSize: 13,
                          color: kGray)),
                  const SizedBox(height: 20),
                  if (place.safeDescription.isNotEmpty) ...[
                    Text('About',
                        style: GoogleFonts.inter(
                            fontSize: 15,
                            fontWeight:
                                FontWeight.w700,
                            color: kDark)),
                    const SizedBox(height: 6),
                    Text(place.safeDescription,
                        style: GoogleFonts.inter(
                            fontSize: 14,
                            color: kDark,
                            height: 1.6)),
                    const SizedBox(height: 20),
                  ],
                  if (place.safeHistory.isNotEmpty) ...[
                    Text('History',
                        style: GoogleFonts.inter(
                            fontSize: 15,
                            fontWeight:
                                FontWeight.w700,
                            color: kDark)),
                    const SizedBox(height: 6),
                    Text(place.safeHistory,
                        style: GoogleFonts.inter(
                            fontSize: 14,
                            color: kGray,
                            height: 1.6)),
                    const SizedBox(height: 20),
                  ],
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      if (place.safeHasTicket)
                        _infoChip(
                            Icons
                                .confirmation_number_outlined,
                            'Entry ticket required'),
                      _infoChip(
                          Icons.location_on_outlined,
                          '${place.safeLatitude.toStringAsFixed(4)}, ${place.safeLongitude.toStringAsFixed(4)}'),
                      _infoChip(Icons.map_outlined,
                          place.safeProvince),
                    ],
                  ),
                  const SizedBox(height: 80),
                ],
              ),
            ),
          ),
        ],
      ),
      bottomSheet: Container(
        padding:
            const EdgeInsets.fromLTRB(20, 12, 20, 24),
        decoration: const BoxDecoration(
            color: kCardBg,
            border: Border(
                top: BorderSide(color: kBorder))),
        child: SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (_) => MapScreen(
                        places: [place],
                        onBack: () =>
                            Navigator.pop(context)))),
            icon: const Icon(
                Icons.navigation_outlined,
                size: 18),
            label:
                const Text('Navigate from Kathmandu'),
          ),
        ),
      ),
    );
  }

  Widget _infoChip(IconData icon, String label) =>
      Container(
        padding: const EdgeInsets.symmetric(
            horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
            color: kCardBg,
            borderRadius:
                BorderRadius.circular(20),
            border: Border.all(color: kBorder)),
        child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 14, color: kGray),
              const SizedBox(width: 6),
              Text(label,
                  style: GoogleFonts.inter(
                      fontSize: 12,
                      color: kGray,
                      fontWeight:
                          FontWeight.w500)),
            ]),
      );
}