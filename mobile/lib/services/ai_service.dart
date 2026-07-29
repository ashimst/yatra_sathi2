import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:mobile/constants.dart';
import 'package:mobile/services/auth_service.dart';

class AIService {
  /// Send a chat turn to the AI assistant.  This is the canonical entry
  /// point for all chat interaction — [AIChatWidget] uses this instead of
  /// making raw http calls so authentication, session ids, and context
  /// fields stay consistent across the whole app.
  static Future<Map<String, dynamic>> chat({
    required String sessionId,
    required String message,
    String? userId,
    String? screenContext,
    Map<String, dynamic>? screenData,
    Map<String, dynamic>? itineraryContext,
    List<Map<String, dynamic>>? createdItineraries,
  }) async {
    final headers = await AuthService.getAuthHeader();
    headers['Content-Type'] = 'application/json';

    final body = <String, dynamic>{
      'session_id': sessionId,
      'message': message,
    };
    if (userId != null) body['user_id'] = userId;
    if (screenContext != null) body['screen_context'] = screenContext;
    if (screenData != null) body['screen_data'] = screenData;
    if (itineraryContext != null) body['itinerary_context'] = itineraryContext;
    if (createdItineraries != null) {
      body['created_itineraries'] = createdItineraries;
    }

    final response = await http
        .post(
          Uri.parse('$kBaseUrl/ai/chat'),
          headers: headers,
          body: json.encode(body),
        )
        .timeout(const Duration(seconds: 90));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      try {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ??
            'AI chat failed (status ${response.statusCode})');
      } on FormatException catch (_) {
        throw Exception('AI chat failed (status ${response.statusCode}): '
            '${response.body}');
      }
    }
  }

  /// Get session information (chat history + metadata).
  static Future<Map<String, dynamic>> getSession(String sessionId) async {
    final headers = await AuthService.getAuthHeader();

    final response = await http
        .get(
          Uri.parse('$kBaseUrl/ai/sessions/$sessionId'),
          headers: headers,
        )
        .timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else if (response.statusCode == 404) {
      throw Exception('Session not found');
    } else {
      throw Exception('Failed to fetch session');
    }
  }

  /// Delete a session and clear its chat history.
  static Future<void> deleteSession(String sessionId) async {
    final headers = await AuthService.getAuthHeader();

    final response = await http
        .delete(
          Uri.parse('$kBaseUrl/ai/sessions/$sessionId'),
          headers: headers,
        )
        .timeout(const Duration(seconds: 10));

    if (response.statusCode != 200) {
      throw Exception('Failed to delete session');
    }
  }

  /// Ask the AI to propose edits to a given itinerary in a single call.
  static Future<Map<String, dynamic>> editItinerary({
    required Map<String, dynamic> currentItinerary,
    required String editRequest,
    String? userId,
  }) async {
    final headers = await AuthService.getAuthHeader();
    headers['Content-Type'] = 'application/json';

    final body = <String, dynamic>{
      'current_itinerary': currentItinerary,
      'edit_request': editRequest,
    };
    if (userId != null) body['user_id'] = userId;

    final response = await http
        .post(
          Uri.parse('$kBaseUrl/ai/edit-itinerary'),
          headers: headers,
          body: json.encode(body),
        )
        .timeout(const Duration(seconds: 90));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      try {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ??
            'AI itinerary edit failed (status ${response.statusCode})');
      } on FormatException catch (_) {
        throw Exception('AI itinerary edit failed (status '
            '${response.statusCode}): ${response.body}');
      }
    }
  }

  /// Generate a unique, collision-resistant session id.
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
