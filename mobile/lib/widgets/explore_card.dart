import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/widgets/placeholder_image.dart';

class ExploreCard extends StatelessWidget {
  final Place place;
  final bool isSaved;
  final VoidCallback onSave;
  final VoidCallback onTap;

  const ExploreCard({
    super.key,
    required this.place,
    required this.isSaved,
    required this.onSave,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: kCardBg,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: kBorder),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Stack(
                children: [
                  ClipRRect(
                    borderRadius: const BorderRadius.only(
                        topLeft: Radius.circular(15),
                        topRight: Radius.circular(15)),
                    child: place.imageUrl.isNotEmpty
                        ? Image.network(place.imageUrl,
                            width: double.infinity,
                            height: double.infinity,
                            fit: BoxFit.cover,
                            errorBuilder: (c, e, s) =>
                                buildPlaceholderImage(
                                    place.category,
                                    width: 200,
                                    height: 200))
                        : buildPlaceholderImage(place.category,
                            width: 200, height: 200),
                  ),
                  Positioned(
                    top: 8,
                    right: 8,
                    child: GestureDetector(
                      onTap: onSave,
                      child: Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.9),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          isSaved
                              ? Icons.favorite
                              : Icons.favorite_border,
                          size: 16,
                          color: isSaved ? kOrange : kGray,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(place.name,
                      style: GoogleFonts.inter(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: kDark),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis),
                  Text(
                      place.safeDistrict.isNotEmpty
                          ? place.safeDistrict
                          : place.category,
                      style: GoogleFonts.inter(
                          fontSize: 11, color: kGray),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}