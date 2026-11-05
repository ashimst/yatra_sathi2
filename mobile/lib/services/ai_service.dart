import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:mobile/constants.dart';
import 'package:mobile/services/auth_service.dart';

class AIService {
  // Send chat message to AI assistant
  static Future<Map<String, dynamic>> chat({
    required String sessionId,
    required String message,
    String? userId,
  }) async {
    final headers = await AuthService.getAuthHeader();
    headers['Content-Type'] = 'application/json';

    final response = await http.post(
      Uri.parse('$kBaseUrl/ai/chat'),
      headers: headers,
      body: json.encode({
        'session_id': sessionId,
        'user_id': userId,
        'message': message,
      }),
    ).timeout(const Duration(seconds: 90));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      final error = json.decode(response.body);
      throw Exception(error['detail'] ?? 'AI chat failed');
    }
  }

  // Get session information
  static Future<Map<String, dynamic>> getSession(String sessionId) async {
    final headers = await AuthService.getAuthHeader();

    final response = await http.get(
      Uri.parse('$kBaseUrl/ai/sessions/$sessionId'),
      headers: headers,
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else if (response.statusCode == 404) {
      throw Exception('Session not found');
    } else {
      throw Exception('Failed to fetch session');
    }
  }

  // Delete session
  static Future<void> deleteSession(String sessionId) async {
    final headers = await AuthService.getAuthHeader();

    final response = await http.delete(
      Uri.parse('$kBaseUrl/ai/sessions/$sessionId'),
      headers: headers,
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode != 200) {
      throw Exception('Failed to delete session');
    }
  }

  // Edit itinerary with AI
  static Future<Map<String, dynamic>> editItinerary({
    required Map<String, dynamic> currentItinerary,
    required String editRequest,
  }) async {
    final headers = await AuthService.getAuthHeader();
    headers['Content-Type'] = 'application/json';

    final response = await http.post(
      Uri.parse('$kBaseUrl/ai/edit-itinerary'),
      headers: headers,
      body: json.encode({
        'current_itinerary': currentItinerary,
        'edit_request': editRequest,
      }),
    ).timeout(const Duration(seconds: 90));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      final error = json.decode(response.body);
      throw Exception(error['detail'] ?? 'AI itinerary edit failed');
    }
  }

  // Generate unique session ID
  static String generateSessionId() {
    return 'session_${DateTime.now().millisecondsSinceEpoch}_${_randomString(8)}';
  }

  static String _randomString(int length) {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    final random = DateTime.now().millisecondsSinceEpoch;
    String result = '';
    for (int i = 0; i < length; i++) {
      result += chars[(random + i) % chars.length];
    }
    return result;
  }
}
