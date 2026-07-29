import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:mobile/constants.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  static const String _tokenKey = 'auth_token';
  static const String _userKey = 'user_data';

  // Register new user
  static Future<Map<String, dynamic>> register({
    required String email,
    required String username,
    required String password,
    String? fullName,
  }) async {
    final response = await http.post(
      Uri.parse('$kBaseUrl/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'email': email,
        'username': username,
        'password': password,
        'full_name': fullName,
      }),
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      await _saveToken(data['access_token']);
      await _saveUser(data['user']);
      return data;
    } else {
      final error = json.decode(response.body);
      throw Exception(error['detail'] ?? 'Registration failed');
    }
  }

  // Login user
  static Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$kBaseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'email': email,
        'password': password,
      }),
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      await _saveToken(data['access_token']);
      await _saveUser(data['user']);
      return data;
    } else {
      final error = json.decode(response.body);
      throw Exception(error['detail'] ?? 'Login failed');
    }
  }

  // Get current user profile
  static Future<Map<String, dynamic>> getCurrentUser() async {
    final token = await getToken();
    if (token == null) {
      throw Exception('Not authenticated');
    }

    final response = await http.get(
      Uri.parse('$kBaseUrl/auth/me'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    ).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to get user profile');
    }
  }

  // Logout
  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_userKey);
  }

  // Check if user is authenticated
  static Future<bool> isAuthenticated() async {
    final token = await getToken();
    return token != null;
  }

  // Get stored token
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  // Get stored user data
  static Future<Map<String, dynamic>?> getUser() async {
    final prefs = await SharedPreferences.getInstance();
    final userJson = prefs.getString(_userKey);
    if (userJson != null) {
      return json.decode(userJson);
    }
    return null;
  }

  // Save token locally
  static Future<void> _saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  // Save user data locally
  static Future<void> _saveUser(Map<String, dynamic> user) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userKey, json.encode(user));
  }

  // Get authorization header
  static Future<Map<String, String>> getAuthHeader() async {
    final token = await getToken();
    if (token != null) {
      return {'Authorization': 'Bearer $token'};
    }
    return {};
  }
}
