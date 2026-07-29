import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/services/user_session.dart';
import 'package:mobile/screens/place_detail_screen.dart';
import 'package:mobile/widgets/placeholder_image.dart';

class TrendingListTile extends StatelessWidget {
  final Place place;
  final VoidCallback onToggleSave;

  const TrendingListTile({
    super.key,
    required this.place,
    required this.onToggleSave,
  });

  @override
  Widget build(BuildContext context) {
    final saved = UserSession.savedPlaceIds.contains(place.id);
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: kBorder),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: ListTile(
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          tileColor: kCardBg,
          leading: ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: place.imageUrl.isNotEmpty
                ? Image.network(place.imageUrl,
                    width: 56,
                    height: 56,
                    fit: BoxFit.cover,
                    errorBuilder: (c, e, s) =>
                        buildPlaceholderImage(place.category))
                : buildPlaceholderImage(place.category),
          ),
          title: Text(place.name,
              style: GoogleFonts.inter(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: kDark)),
          subtitle: Text(place.safeDistrict,
              style: GoogleFonts.inter(fontSize: 13, color: kGray)),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              GestureDetector(
                onTap: onToggleSave,
                child: Icon(
                    saved ? Icons.favorite : Icons.favorite_border,
                    color: kOrange,
                    size: 20),
              ),
              const SizedBox(width: 10),
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: kOrange.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.star,
                        size: 14, color: kOrange),
                    const SizedBox(width: 3),
                    Text(place.safeRating.toStringAsFixed(1),
                        style: GoogleFonts.inter(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: kOrange)),
                  ],
                ),
              ),
            ],
          ),
          onTap: () {
            Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (_) =>
                        PlaceDetailScreen(place: place)));
          },
        ),
      ),
    );
  }
}