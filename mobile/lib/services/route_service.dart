import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:mobile/constants.dart';

class RouteService {
  Future<Map<String, dynamic>> getRoute(
      LatLng origin, LatLng destination) async {
    try {
      final res = await http.post(
        Uri.parse('$kBaseUrl/route'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'origin_lat': origin.latitude,
          'origin_lng': origin.longitude,
          'dest_lat': destination.latitude,
          'dest_lng': destination.longitude,
        }),
      ).timeout(const Duration(seconds: 30));

      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      } else {
        final detail = _parseError(res.body);
        throw Exception(detail);
      }
    } catch (e) {
      throw Exception('Route service error: $e');
    }
  }

  Future<Map<String, dynamic>> getMultiRoute(
      List<LatLng> waypoints) async {
    if (waypoints.length < 2) {
      throw Exception('At least 2 waypoints required for routing');
    }
    
    try {
      final coords = waypoints
          .map((wp) => [wp.longitude, wp.latitude])
          .toList();
      final res = await http.post(
        Uri.parse('$kBaseUrl/route'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'waypoints': coords}),
      ).timeout(const Duration(seconds: 30));

      if (res.statusCode == 200) {
        return json.decode(res.body) as Map<String, dynamic>;
      } else {
        final detail = _parseError(res.body);
        throw Exception(detail);
      }
    } catch (e) {
      throw Exception('Multi-route service error: $e');
    }
  }

  String _parseError(String body) {
    try {
      final data = json.decode(body);
      return data['detail'] ?? 'Unknown error';
    } catch (_) {
      return 'Server error';
    }
  }
}