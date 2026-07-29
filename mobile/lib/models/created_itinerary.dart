import 'package:latlong2/latlong.dart';
import 'package:mobile/models/place.dart';

class CreatedItinerary {
  final String id;
  String title;
  final String from;
  final String to;
  final int days;
  final int travelers;
  final String budget;
  final String pace;
  final String diet;
  final String author;
  int likes;
  bool isPublic;
  final Map<String, List<Map<String, dynamic>>> itinerary;
  final List<Place> orderedWaypoints;
  final List<LatLng> routePoints;
  final double distanceKm;
  final double durationMinutes;

  CreatedItinerary({
    required this.id,
    required this.title,
    required this.from,
    required this.to,
    required this.days,
    required this.travelers,
    required this.budget,
    required this.pace,
    required this.diet,
    required this.author,
    this.likes = 0,
    this.isPublic = false,
    required this.itinerary,
    required this.orderedWaypoints,
    required this.routePoints,
    required this.distanceKm,
    required this.durationMinutes,
  });
}