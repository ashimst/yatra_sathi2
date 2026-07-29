import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:mobile/constants.dart';
import 'package:geolocator/geolocator.dart';

class WeatherService {
  Future<Map<String, dynamic>> getCurrentWeather() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Location services are disabled.');
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.deniedForever) {
      throw Exception('Location permissions are denied forever.');
    }

    final pos = await Geolocator.getCurrentPosition(
        locationSettings:
            const LocationSettings(accuracy: LocationAccuracy.low));
    final url =
        'https://api.openweathermap.org/data/2.5/weather?lat=${pos.latitude}&lon=${pos.longitude}&units=metric&appid=$kOpenWeatherApiKey';
    final res =
        await http.get(Uri.parse(url)).timeout(const Duration(seconds: 8));

    if (res.statusCode == 200) {
      final data = json.decode(res.body) as Map<String, dynamic>;
      final main = data['main'] as Map<String, dynamic>?;
      final weather = (data['weather'] as List?)
          ?.cast<Map<String, dynamic>>();
      return {
        'city': data['name'] ?? 'Local Area',
        'temp': (main?['temp'] as num?)?.round() ?? 23,
        'description':
            weather?.first['description'] as String? ?? 'Clear sky',
      };
    } else {
      throw Exception('Weather fetch failed');
    }
  }
}