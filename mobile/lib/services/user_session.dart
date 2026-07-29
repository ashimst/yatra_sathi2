import 'package:mobile/models/place.dart';
import 'package:mobile/models/created_itinerary.dart';
import 'package:mobile/services/user_storage.dart';
import 'package:latlong2/latlong.dart';

class UserSession {
  static String? loggedInUser;
  static String? email;
  static Set<String> savedPlaceIds = {};
  static List<CreatedItinerary> savedItineraries = [];
  static List<CreatedItinerary> publicItineraries = [
    CreatedItinerary(
      id: 'pub1',
      title: 'A monsoon weekend in Bandipur',
      from: 'Kathmandu',
      to: 'Bandipur',
      days: 2,
      travelers: 1,
      budget: 'Rs 10,000',
      pace: 'Balanced',
      diet: 'Veg',
      author: 'Sita',
      likes: 248,
      isPublic: true,
      itinerary: {
        'Day 1': [
          {
            'time': '9:00 AM',
            'name': 'Thani Mai Temple Viewpoint',
            'category': 'Spirituality',
            'duration': '2 hrs'
          },
          {
            'time': '2:00 PM',
            'name': 'Siddha Gufa Cave',
            'category': 'Adventure',
            'duration': '3 hrs'
          },
          {
            'time': '7:00 PM',
            'name': 'Local Newari dinner',
            'category': 'Food',
            'duration': '1 hr'
          }
        ]
      },
      orderedWaypoints: [
        Place(
            id: 'start',
            name: 'Kathmandu',
            category: 'Origin',
            district: '',
            province: '',
            city: 'Kathmandu',
            description: '',
            history: '',
            latitude: 27.7172,
            longitude: 85.3240,
            images: [],
            hasTicket: false),
        Place(
            id: 'w1',
            name: 'Bandipur Bazaar',
            category: 'Culture',
            district: 'Tanahun',
            province: 'Gandaki',
            city: 'Bandipur',
            description: '',
            history: '',
            latitude: 27.9389,
            longitude: 84.4167,
            images: [],
            hasTicket: false),
        Place(
            id: 'end',
            name: 'Bandipur',
            category: 'Destination',
            district: '',
            province: '',
            city: 'Bandipur',
            description: '',
            history: '',
            latitude: 27.9389,
            longitude: 84.4167,
            images: [],
            hasTicket: false)
      ],
      routePoints: [
        const LatLng(27.7172, 85.3240),
        const LatLng(27.9389, 84.4167)
      ],
      distanceKm: 148.0,
      durationMinutes: 240.0,
    ),
    CreatedItinerary(
      id: 'pub2',
      title: 'Family loop through Chitwan',
      from: 'Kathmandu',
      to: 'Chitwan',
      days: 5,
      travelers: 4,
      budget: 'Rs 70,000',
      pace: 'Relaxed',
      diet: 'Non-veg',
      author: 'Rohan',
      likes: 412,
      isPublic: true,
      itinerary: {
        'Day 1': [
          {
            'time': '10:00 AM',
            'name': 'Chitwan National Park Safari',
            'category': 'Wildlife',
            'duration': '4 hrs'
          },
          {
            'time': '7:00 PM',
            'name': 'Tharu Culture Dance Show',
            'category': 'Culture',
            'duration': '2 hrs'
          }
        ]
      },
      orderedWaypoints: [
        Place(
            id: 'start',
            name: 'Kathmandu',
            category: 'Origin',
            district: '',
            province: '',
            city: 'Kathmandu',
            description: '',
            history: '',
            latitude: 27.7172,
            longitude: 85.3240,
            images: [],
            hasTicket: false),
        Place(
            id: 'w1',
            name: 'Sauraha Chitwan',
            category: 'Wildlife',
            district: 'Chitwan',
            province: 'Bagmati',
            city: 'Chitwan',
            description: '',
            history: '',
            latitude: 27.5291,
            longitude: 84.3542,
            images: [],
            hasTicket: false),
        Place(
            id: 'end',
            name: 'Chitwan',
            category: 'Destination',
            district: '',
            province: '',
            city: 'Chitwan',
            description: '',
            history: '',
            latitude: 27.5291,
            longitude: 84.3542,
            images: [],
            hasTicket: false)
      ],
      routePoints: [
        const LatLng(27.7172, 85.3240),
        const LatLng(27.5291, 84.3542)
      ],
      distanceKm: 160.0,
      durationMinutes: 300.0,
    ),
  ];

  static Future<void> loadFromStorage() async {
    final session = await UserStorage.loadSession();
    loggedInUser = session['user'];
    email = session['email'];
    savedPlaceIds = await UserStorage.loadPlaceIds();
  }

  static Future<void> clearSessionOnLogout() async {
    loggedInUser = null;
    email = null;
    await UserStorage.clearSession();
  }

  static Future<void> persist() async {
    if (loggedInUser != null && email != null) {
      await UserStorage.saveSession(
          user: loggedInUser!, email: email!);
    }
    await UserStorage.savePlaceIds(savedPlaceIds);
  }

  static String initials(String? name) {
    final value = (name ?? 'EX').trim();
    if (value.isEmpty) return 'EX';
    if (value.length == 1) return value.toUpperCase();
    return value.substring(0, 2).toUpperCase();
  }
}