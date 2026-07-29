import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:mobile/constants.dart';
import 'package:mobile/services/auth_service.dart';

class ItineraryService {
  // Create new itinerary
  static Future<Map<String, dynamic>> createItinerary({
    required String title,
    String? description,
    required String origin,
    required String destination,
    required int days,
    int travelers = 1,
    String? budget,
    String? pace,
    String? diet,
    required Map<String, dynamic> itineraryData,
    List<List<double>>? waypoints,
    List<List<double>>? routePoints,
    double? distanceKm,
    double? durationMinutes,
    bool isPublic = false,
  }) async {
    final headers = await AuthService.getAuthHeader();
    headers['Content-Type'] = 'application/json';

    final response = await http.post(
      Uri.parse('$kBaseUrl/itineraries'),
      headers: headers,
      body: json.encode({
        'title': title,
        'description': description,
        'origin': origin,
        'destination': destination,
        'days': days,
        'travelers': travelers,
        'budget': budget,
        'pace': pace,
        'diet': diet,
        'itinerary_data': itineraryData,
        'waypoints': waypoints,
        'route_points': routePoints,
        'distance_km': distanceKm,
        'duration_minutes': durationMinutes,
        'is_public': isPublic,
      }),
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      final error = json.decode(response.body);
      throw Exception(error['detail'] ?? 'Failed to create itinerary');
    }
  }

  // Get user's itineraries
  static Future<List<Map<String, dynamic>>> getMyItineraries() async {
    final headers = await AuthService.getAuthHeader();

    final response = await http.get(
      Uri.parse('$kBaseUrl/itineraries'),
      headers: headers,
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return List<Map<String, dynamic>>.from(data['itineraries']);
    } else {
      throw Exception('Failed to fetch itineraries');
    }
  }

  // Get public itineraries
  static Future<List<Map<String, dynamic>>> getPublicItineraries() async {
    final response = await http.get(
      Uri.parse('$kBaseUrl/itineraries/public'),
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return List<Map<String, dynamic>>.from(data['itineraries']);
    } else {
      throw Exception('Failed to fetch public itineraries');
    }
  }

  // Get specific itinerary
  static Future<Map<String, dynamic>> getItinerary(String id) async {
    final headers = await AuthService.getAuthHeader();

    final response = await http.get(
      Uri.parse('$kBaseUrl/itineraries/$id'),
      headers: headers,
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else if (response.statusCode == 404) {
      throw Exception('Itinerary not found');
    } else {
      throw Exception('Failed to fetch itinerary');
    }
  }

  // Update itinerary
  static Future<Map<String, dynamic>> updateItinerary(
    String id, {
    String? title,
    String? description,
    Map<String, dynamic>? itineraryData,
    bool? isPublic,
  }) async {
    final headers = await AuthService.getAuthHeader();
    headers['Content-Type'] = 'application/json';

    final body = <String, dynamic>{};
    if (title != null) body['title'] = title;
    if (description != null) body['description'] = description;
    if (itineraryData != null) body['itinerary_data'] = itineraryData;
    if (isPublic != null) body['is_public'] = isPublic;

    final response = await http.put(
      Uri.parse('$kBaseUrl/itineraries/$id'),
      headers: headers,
      body: json.encode(body),
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to update itinerary');
    }
  }

  // Delete itinerary
  static Future<void> deleteItinerary(String id) async {
    final headers = await AuthService.getAuthHeader();

    final response = await http.delete(
      Uri.parse('$kBaseUrl/itineraries/$id'),
      headers: headers,
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode != 200) {
      throw Exception('Failed to delete itinerary');
    }
  }

  // Like an itinerary
  static Future<Map<String, dynamic>> likeItinerary(String id) async {
    final response = await http.post(
      Uri.parse('$kBaseUrl/itineraries/$id/like'),
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to like itinerary');
    }
  }
}
