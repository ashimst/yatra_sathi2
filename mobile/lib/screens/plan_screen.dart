import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';
import 'package:http/http.dart' as http;
import 'package:mobile/constants.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/models/created_itinerary.dart';
import 'package:mobile/services/user_session.dart';
import 'package:mobile/services/route_service.dart';
import 'package:mobile/utils/geo.dart';
import 'package:mobile/screens/place_detail_screen.dart';
import 'package:mobile/widgets/day_section.dart';
import 'package:mobile/widgets/ai_chat_widget.dart';

class PlanScreen extends StatefulWidget {
  final List<Place> places;
  const PlanScreen({super.key, required this.places});

  @override
  State<PlanScreen> createState() => _PlanScreenState();
}

class _PlanScreenState extends State<PlanScreen> {
  String _from = 'Kathmandu', _to = 'Pokhara';
  DateTimeRange? _dateRange;
  int _travelers = 2;
  String _travelTime = 'Morning';
  double _stayBudget = 4500;
  double _foodBudget = 1200;
  String _diet = 'Veg';
  final Set<String> _interests = {'Nature'};
  String _pace = 'Balanced';
  bool _isGenerating = false;
  bool _isLoading = false;
  Map<String, dynamic>? _generatedItinerary;

  Place? _selectedItineraryPlace;

  List<LatLng> _itineraryRoutePoints = [];
  bool _isItineraryRouteLoading = false;
  double? _itineraryDistance;
  double? _itineraryDuration;
  
  List<LatLng> _osrmRoutePoints = [];
  List<Place> _nearbyPois = [];

  final List<String> _nepalCities = [
    'Kathmandu',
    'Pokhara',
    'Chitwan',
    'Lumbini',
    'Bhaktapur',
    'Patan',
    'Janakpur',
    'Bandipur'
  ];
  final List<String> _travelTimes =
      ['Morning', 'Day', 'Evening', 'Night'];
  final List<String> _dietOptions =
      ['Veg', 'Non-veg', 'Vegan'];
  final List<String> _interestOptions = [
    'Nature',
    'Adventure',
    'Culture',
    'Photography',
    'Food',
    'Spirituality',
    'Nightlife',
    'Hidden gems'
  ];
  final List<String> _paceOptions =
      ['Relaxed', 'Balanced', 'Fast-paced'];

  LatLng _getCityCoords(String city) {
    switch (city.toLowerCase()) {
      case 'kathmandu':
        return const LatLng(27.7172, 85.3240);
      case 'pokhara':
        return const LatLng(28.2096, 83.9856);
      case 'chitwan':
        return const LatLng(27.5291, 84.3542);
      case 'lumbini':
        return const LatLng(27.4789, 83.2755);
      case 'bhaktapur':
        return const LatLng(27.6710, 85.4298);
      case 'patan':
        return const LatLng(27.6766, 85.3149);
      case 'janakpur':
        return const LatLng(26.7278, 85.9238);
      case 'bandipur':
        return const LatLng(27.9389, 84.4167);
      default:
        return const LatLng(27.7172, 85.3240);
    }
  }

  String _formatTime(String? backendTime, int fallbackHour) {
    if (backendTime != null && backendTime.isNotEmpty) {
      // Convert HH:MM to 12-hour friendly format
      try {
        final parts = backendTime.split(':');
        final h = int.parse(parts[0]);
        final m = int.parse(parts[1]);
        final suffix = h >= 12 ? 'PM' : 'AM';
        final hour12 = h == 0 ? 12 : (h > 12 ? h - 12 : h);
        return '$hour12:${m.toString().padLeft(2, '0')} $suffix';
      } catch (_) {
        return backendTime;
      }
    }
    return '$fallbackHour:00 ${fallbackHour < 12 ? 'AM' : 'PM'}';
  }

  String _formatDuration(num? hours, String? fallbackVisitDuration) {
    if (hours != null && hours > 0) {
      if (hours < 1) {
        return '${(hours * 60).round()} min';
      }
      final h = hours.floor();
      final m = ((hours - h) * 60).round();
      if (m == 0) return h == 1 ? '1 hr' : '$h hrs';
      return '$h–${h + 1} hrs';
    }
    if (fallbackVisitDuration != null && fallbackVisitDuration.isNotEmpty) {
      return fallbackVisitDuration;
    }
    return '1–2 hrs';
  }

  Future<void> _generateItinerary() async {
    if (_dateRange == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Please select travel dates')),
      );
      return;
    }
    if (!mounted) return;
    setState(() {
      _isGenerating = true;
      _generatedItinerary = null;
    });

    final days =
        (_dateRange!.duration.inDays + 1).clamp(1, 30);
    final originCoords = _getCityCoords(_from);
    final destCoords = _getCityCoords(_to);
    final maxStopsPerDay = _pace == 'Relaxed'
        ? 2
        : (_pace == 'Fast-paced' ? 4 : 3);

    List<Place> relevantPlaces = [];
    List<Place> nearbyPois = [];
    List<LatLng> osrmRoutePoints = [];
    // Direct backend day-plan consumption
    final backendDayItinerary = <String, List<Map<String, dynamic>>>{};
    final orderedWaypointsFromBackend = <Place>[];

    if (!mounted) return;
    setState(() {
      _osrmRoutePoints = [];
      _nearbyPois = [];
    });

    try {
      // Include dietary_preferences in query params; send pace with correct casing
      final queryParams = <String, String>{
        'origin_lat': originCoords.latitude.toString(),
        'origin_lng': originCoords.longitude.toString(),
        'dest_lat': destCoords.latitude.toString(),
        'dest_lng': destCoords.longitude.toString(),
        'corridor_km': '20',
        'generate_itinerary': 'true',
        'num_days': days.toString(),
        'travel_style': _pace.toLowerCase(),
        'budget': 'medium',
        'user_preferences': _interests.join(','),
        'dietary_preferences': _diet,
      };
      final recUrl = Uri.parse('$kBaseUrl/recommend')
          .replace(queryParameters: queryParams);
      final recRes = await http
          .get(recUrl)
          .timeout(const Duration(seconds: 90));
      debugPrint('Recommendation response status: ${recRes.statusCode}');
      debugPrint('Recommendation response body length: ${recRes.body.length}');
      if (recRes.statusCode == 200) {
        final recData = json.decode(recRes.body);
        debugPrint('Recommendation response keys: ${recData.keys}');
        debugPrint('Has itinerary key: ${recData.containsKey('itinerary')}');
        debugPrint('Has recommended_destinations key: ${recData.containsKey('recommended_destinations')}');
        debugPrint('Has route key: ${recData.containsKey('route')}');

        // Extract OSRM route from backend response
        if (recData['route'] != null && recData['route']['coordinates'] != null) {
          final coords = recData['route']['coordinates'] as List;
          osrmRoutePoints = coords
              .map((c) {
            if (c is List && c.length >= 2) {
              return LatLng(
                  (c[1] as num).toDouble(),
                  (c[0] as num).toDouble());
            }
            return null;
          })
              .where((latLng) => latLng != null)
              .cast<LatLng>()
              .toList();
          debugPrint('OSRM route loaded: ${osrmRoutePoints.length} points');
        } else {
          // LLM success case: route key is missing at top-level. Fallback: fetch via RouteService.
          debugPrint('No route key in recommendation response; fetching OSRM route separately');
          try {
            final routeData = await RouteService().getRoute(originCoords, destCoords);
            if (routeData['coordinates'] != null) {
              final coords = routeData['coordinates'] as List;
              osrmRoutePoints = coords
                  .map((c) {
                if (c is List && c.length >= 2) {
                  return LatLng(
                      (c[1] as num).toDouble(),
                      (c[0] as num).toDouble());
                }
                return null;
              })
                  .where((latLng) => latLng != null)
                  .cast<LatLng>()
                  .toList();
              debugPrint('Fetched OSRM route separately: ${osrmRoutePoints.length} points');
              // Also stash distance/duration values if available
              if (routeData['distance_km'] != null && _itineraryDistance == null) {
                _itineraryDistance = (routeData['distance_km'] as num).toDouble();
              }
              if (routeData['duration_minutes'] != null && _itineraryDuration == null) {
                _itineraryDuration = (routeData['duration_minutes'] as num).toDouble();
              }
            }
          } catch (rErr) {
            debugPrint('Failed to fetch fallback route: $rErr');
          }
        }

        if (recData['itinerary'] != null) {
          // Handle structured itinerary response format (LLM or fallback)
          debugPrint('Processing itinerary response');
          final itinerary = recData['itinerary'] as Map<String, dynamic>;
          final daysList = itinerary['days'] as List? ?? [];
          debugPrint('Itinerary contains ${daysList.length} day entries');

          orderedWaypointsFromBackend.add(Place(
            id: 'start',
            name: _from,
            category: 'Origin',
            district: '',
            province: '',
            city: _from,
            description: 'Starting location',
            history: '',
            latitude: originCoords.latitude,
            longitude: originCoords.longitude,
            images: [],
            hasTicket: false,
          ));

          for (int dayIdx = 0; dayIdx < daysList.length; dayIdx++) {
            final dayData = daysList[dayIdx] as Map<String, dynamic>;
            final dayNumber = (dayData['day'] as num?)?.toInt() ?? (dayIdx + 1);
            final dayKey = 'Day $dayNumber';
            final dayStops = <Map<String, dynamic>>[];

            // Track if we added overnight for this day (added at the end of loop)
            Place? overnightPlace;

            // Add ACTIVITIES — works for both LLM format (has start_time/description/notes) and fallback
            final activities = dayData['activities'] as List? ?? [];
            int activityIndex = 0;
            for (var rawActivity in activities) {
              final act = Map<String, dynamic>.from(rawActivity as Map);
              final place = Place.fromJson(act);
              // Supplement Place description with LLM description if present
              final llmDesc = act['description'] as String?;
              if (llmDesc != null && llmDesc.isNotEmpty) {
                place.description = place.description ?? llmDesc;
                if (place.description == null || place.description!.isEmpty) {
                  place.description = llmDesc;
                }
              }
              relevantPlaces.add(place);
              orderedWaypointsFromBackend.add(place);

              // Compute time / duration strings depending on format
              final startTime = act['start_time'] as String?;
              final fallbackHour = 9 + activityIndex * 3;
              final timeStr = _formatTime(startTime, fallbackHour.clamp(8, 20));
              final durationHours = act['duration_hours'] as num?;
              final visitDur = place.visitDuration;
              final durationStr = _formatDuration(durationHours, visitDur);

              final cat = place.category.isNotEmpty ? place.category : (act['activity_type'] as String? ?? 'Activity');

              dayStops.add({
                'time': timeStr,
                'name': place.name.isEmpty ? (act['poi_name'] ?? 'Activity') : place.name,
                'category': cat,
                'duration': durationStr,
                'place': place,
                if (act['notes'] != null) 'notes': act['notes'],
              });
              activityIndex++;
            }

            // Add MEALS from fallback format (LLM embeds restaurants into activities)
            final meals = dayData['meals'] as List? ?? [];
            for (var rawMeal in meals) {
              final meal = Map<String, dynamic>.from(rawMeal as Map);
              // Try to infer category as Restaurant if missing
              if (!meal.containsKey('category')) {
                meal['category'] = 'Restaurant';
              }
              final place = Place.fromJson(meal);
              relevantPlaces.add(place);
              orderedWaypointsFromBackend.add(place);

              // Pick lunch or dinner slot based on position
              final isLunch = meals.indexOf(rawMeal) == 0 || dayStops.isEmpty;
              final timeStr = isLunch ? '12:30 PM' : '7:30 PM';
              dayStops.add({
                'time': timeStr,
                'name': place.name.isEmpty ? (meal['name'] ?? 'Meal stop') : place.name,
                'category': place.category.isNotEmpty ? place.category : 'Restaurant',
                'duration': '1 hr',
                'place': place,
              });
            }

            // Add OVERNIGHT ACCOMMODATION (handles both LLM and fallback formats)
            final overnight = dayData['overnight_accommodation'] as Map<String, dynamic>?;
            if (overnight != null) {
              final ov = Map<String, dynamic>.from(overnight);
              if (!ov.containsKey('category')) {
                ov['category'] = 'Accommodation';
              }
              final place = Place.fromJson(ov);
              final llmDesc = ov['description'] as String?;
              if (llmDesc != null && (place.description == null || place.description!.isEmpty)) {
                place.description = llmDesc;
              }
              relevantPlaces.add(place);
              overnightPlace = place;

              dayStops.add({
                'time': '8:00 PM',
                'name': place.name.isEmpty ? (ov['poi_name'] ?? 'Overnight stay') : place.name,
                'category': place.category.isNotEmpty ? place.category : 'Accommodation',
                'duration': 'Overnight',
                'place': place,
              });
            }

            if (overnightPlace != null) {
              orderedWaypointsFromBackend.add(overnightPlace!);
            }

            if (dayStops.isNotEmpty) {
              backendDayItinerary[dayKey] = dayStops;
            }
          }

          orderedWaypointsFromBackend.add(Place(
            id: 'end',
            name: _to,
            category: 'Destination',
            district: '',
            province: '',
            city: _to,
            description: 'End location',
            history: '',
            latitude: destCoords.latitude,
            longitude: destCoords.longitude,
            images: [],
            hasTicket: false,
          ));

          debugPrint('Extracted ${relevantPlaces.length} places from ${backendDayItinerary.length} days of itinerary');
        } else if (recData['recommended_destinations'] != null) {
          // Handle simple recommendations response format
          debugPrint('Recommendations count: ${(recData['recommended_destinations'] as List).length}');
          final recs = recData['recommended_destinations'] as List;
          for (var i = 0; i < recs.length && i < 5; i++) {
            final rec = recs[i] as Map<String, dynamic>;
            debugPrint('  Rec ${i + 1}: ${rec['name']}, distance_to_route_km: ${rec['distance_to_route_km']}');
          }
          relevantPlaces = (recData['recommended_destinations'] as List)
              .map((j) {
            final place = Place.fromJson(j);
            debugPrint('Parsed place: ${place.name} (${place.latitude}, ${place.longitude})');
            return place;
          })
              .toList();
        } else {
          debugPrint('No itinerary or recommended_destinations key in response');
        }

        // Store in state
        if (!mounted) return;
        setState(() {
          _osrmRoutePoints = osrmRoutePoints;
          _nearbyPois = nearbyPois; // Empty - only show itinerary places
        });
      } else {
        debugPrint('Recommend endpoint returned status: ${recRes.statusCode}');
        try {
          final errDetail = json.decode(recRes.body)['detail'];
          debugPrint('Error detail: $errDetail');
        } catch (_) {}
      }
    } catch (e) {
      debugPrint('Recommend endpoint error: $e');
    }

    // Filter out any places with invalid coordinates from recommendations
    relevantPlaces = relevantPlaces.where((p) =>
      p.safeLatitude != 0.0 && p.safeLongitude != 0.0
    ).toList();
    debugPrint('After filtering invalid coordinates: ${relevantPlaces.length} places');

    // Build final itinerary map and ordered waypoints
    Map<String, List<Map<String, dynamic>>> finalItinerary;
    List<Place> orderedWaypoints;

    if (backendDayItinerary.isNotEmpty && orderedWaypointsFromBackend.length >= 2) {
      // Use backend's day plan directly — preserves the trip optimizer's sequencing
      debugPrint('Using backend-structured day plan: ${backendDayItinerary.length} days');
      finalItinerary = backendDayItinerary;
      orderedWaypoints = orderedWaypointsFromBackend;
    } else {
      // Fallback: split places evenly across days (old logic for when backend doesn't return day structure)
      debugPrint('No backend day plan from recommendation, using fallback division');
      if (relevantPlaces.isEmpty) {
        debugPrint('No relevant places from recommendation, using built-in fallback');
        debugPrint('Total available places: ${widget.places.length}');
        relevantPlaces = widget.places.where((p) {
          final catLower = (p.category).toLowerCase();
          if (catLower == 'tour operator' ||
              catLower == 'tour agency' ||
              catLower == 'tourist information center')
            return false;
          // Filter out places with invalid coordinates
          if (p.safeLatitude == 0.0 || p.safeLongitude == 0.0) {
            debugPrint('Skipping ${p.name} due to invalid coordinates (0.0, 0.0)');
            return false;
          }
          final distToOrigin = haversineKm(
              p.safeLatitude,
              p.safeLongitude,
              originCoords.latitude,
              originCoords.longitude);
          final distToDest = haversineKm(
              p.safeLatitude,
              p.safeLongitude,
              destCoords.latitude,
              destCoords.longitude);
          final routeDist = haversineKm(
              originCoords.latitude,
              originCoords.longitude,
              destCoords.latitude,
              destCoords.longitude);
          final isNearRoute = (distToOrigin + distToDest) < routeDist * 1.5;
          if (isNearRoute) {
            debugPrint('Including ${p.name} (${p.safeLatitude}, ${p.safeLongitude})');
          }
          return isNearRoute;
        }).toList();
        debugPrint('Fallback found ${relevantPlaces.length} places');
      }

      if (relevantPlaces.isEmpty) {
        debugPrint('Still no places, using mock places');
        relevantPlaces.addAll(_mockPlaces());
        debugPrint('Mock places added: ${relevantPlaces.length}');
      }

      final maxStops = days * maxStopsPerDay;
      if (relevantPlaces.length > maxStops) {
        relevantPlaces =
            relevantPlaces.sublist(0, maxStops);
      }

      finalItinerary = <String, List<Map<String, dynamic>>>{};
      orderedWaypoints = [];

      orderedWaypoints.add(Place(
        id: 'start',
        name: _from,
        category: 'Origin',
        district: '',
        province: '',
        city: _from,
        description: 'Starting location',
        history: '',
        latitude: originCoords.latitude,
        longitude: originCoords.longitude,
        images: [],
        hasTicket: false,
      ));

      final stopsPerDay =
          (relevantPlaces.length / days)
              .ceil()
              .clamp(1, maxStopsPerDay);
      int placeIdx = 0;
      const times = ['9:00 AM', '12:30 PM', '3:00 PM'];
      const durations = ['2–3 hrs', '1–2 hrs', '1–2 hrs'];

      for (int d = 0; d < days; d++) {
        final key = 'Day ${d + 1}';
        final dayPlaces = <Map<String, dynamic>>[];

        for (int s = 0;
            s < stopsPerDay &&
                placeIdx < relevantPlaces.length;
            s++) {
          final p = relevantPlaces[placeIdx++];
          dayPlaces.add({
            'time': times[s],
            'name': p.name,
            'category': p.category,
            'duration': durations[s],
            'place': p,
          });
          orderedWaypoints.add(p);
        }
        dayPlaces.add({
          'time': _travelTime == 'Morning'
              ? '7:00 PM'
              : '8:00 PM',
          'name': _diet == 'Veg'
              ? 'Dal Bhat dinner'
              : 'Local cuisine dinner',
          'category': 'Food',
          'duration': '1 hr',
        });
        finalItinerary[key] = dayPlaces;
      }

      orderedWaypoints.add(Place(
        id: 'end',
        name: _to,
        category: 'Destination',
        district: '',
        province: '',
        city: _to,
        description: 'End location',
        history: '',
        latitude: destCoords.latitude,
        longitude: destCoords.longitude,
        images: [],
        hasTicket: false,
      ));
    }

    if (!mounted) return;
    setState(() {
      _isGenerating = false;
      _generatedItinerary = {
        'from': _from,
        'to': _to,
        'days': days,
        'travelers': _travelers,
        'pace': _pace,
        'interests': _interests.toList(),
        'budget':
            'Rs ${(_stayBudget * days + _foodBudget * days * _travelers).toStringAsFixed(0)}',
        'itinerary': finalItinerary,
        'orderedWaypoints': orderedWaypoints,
      };
    });

    _fetchRouteForItinerary(orderedWaypoints);
  }

  void _openAiChatSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => AIChatWidget(
        screenContext: 'plan',
        screenData: {
          'origin': _from,
          'destination': _to,
          'duration_days': _dateRange?.duration.inDays ?? 0,
          'travelers': _travelers,
          'travel_time': _travelTime,
          'stay_budget': _stayBudget,
          'food_budget': _foodBudget,
          'diet': _diet,
          'interests': _interests.toList(),
          'pace': _pace,
        },
        itineraryContext: _generatedItinerary != null ? {
          'id': 'generated_itinerary',
          'title': 'Generated Itinerary',
          'from': _from,
          'to': _to,
          'days': _dateRange?.duration.inDays ?? 0,
          'itinerary': _generatedItinerary,
        } : null,
        onNavigate: () {
          // Handle navigation if AI suggests moving to a different screen
        },
      ),
    );
  }

  Future<void> _fetchRouteForItinerary(
      List<Place> waypoints) async {
    if (waypoints.length < 2) {
      debugPrint('Not enough waypoints for routing');
      return;
    }
    
    setState(() {
      _isItineraryRouteLoading = true;
      _itineraryRoutePoints = [];
      _itineraryDistance = null;
      _itineraryDuration = null;
    });
    
    try {
      final coords = waypoints
          .map((wp) =>
              LatLng(wp.safeLatitude, wp.safeLongitude))
          .toList();
      
      debugPrint('Fetching route for ${coords.length} waypoints');
      final data = await RouteService().getMultiRoute(coords);
      debugPrint('Route data received: ${data.keys}');
      
      final geometry = data['geometry'];
      if (geometry != null && geometry['coordinates'] != null) {
        final coordsList = geometry['coordinates'] as List;
        debugPrint('Processing ${coordsList.length} route coordinates');
        
        setState(() {
          _itineraryRoutePoints = coordsList
              .map((c) {
                if (c is List && c.length >= 2) {
                  return LatLng(
                      (c[1] as num).toDouble(),
                      (c[0] as num).toDouble());
                }
                return null;
              })
              .where((latLng) => latLng != null)
              .cast<LatLng>()
              .toList();
          _itineraryDistance =
              (data['distance_km'] as num?)
                  ?.toDouble();
          _itineraryDuration =
              (data['duration_minutes'] as num?)
                  ?.toDouble();
        });
        debugPrint('Route loaded: ${_itineraryRoutePoints.length} points, ${_itineraryDistance}km');
      } else {
        debugPrint('Invalid geometry in route response');
      }
    } catch (e) {
      debugPrint('Itinerary multi routing error: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text(
                  'Route loading failed. Using straight-line distances. ${e.toString().split(":").last.trim()}')),
        );
      }
    } finally {
      if (mounted)
        setState(
            () => _isItineraryRouteLoading = false);
    }
  }

  List<Place> _mockPlaces() => [
        Place(
            id: '1',
            name: 'Phewa Lake',
            category: 'Lake',
            district: 'Kaski',
            province: 'Gandaki',
            city: 'Pokhara',
            description: '',
            history: '',
            latitude: 28.2096,
            longitude: 83.9856,
            images: [],
            hasTicket: false),
        Place(
            id: '2',
            name: 'Sarangkot Viewpoint',
            category: 'Tourist attraction',
            district: 'Kaski',
            province: 'Gandaki',
            city: 'Pokhara',
            description: '',
            history: '',
            latitude: 28.2427,
            longitude: 83.9634,
            images: [],
            hasTicket: false),
        Place(
            id: '3',
            name: "Devi's Fall",
            category: 'Tourist attraction',
            district: 'Kaski',
            province: 'Gandaki',
            city: 'Pokhara',
            description: '',
            history: '',
            latitude: 28.1895,
            longitude: 83.9592,
            images: [],
            hasTicket: false),
      ];

  String _monthName(int m) => [
        '',
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'Dec'
      ][m];

  void _saveItinerary() {
    final data = _generatedItinerary;
    if (data == null) return;

    final newIt = CreatedItinerary(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title:
          "Roadtrip from ${data['from']} to ${data['to']}",
      from: data['from'],
      to: data['to'],
      days: data['days'],
      travelers: data['travelers'],
      budget: data['budget'],
      pace: _pace,
      diet: _diet,
      author: UserSession.loggedInUser ?? 'Explorer',
      itinerary: data['itinerary'],
      orderedWaypoints:
          List.from(data['orderedWaypoints']),
      routePoints: List.from(_itineraryRoutePoints),
      distanceKm: _itineraryDistance ?? 0.0,
      durationMinutes: _itineraryDuration ?? 0.0,
    );

    setState(() {
      UserSession.savedItineraries.add(newIt);
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
          content: Text(
              'Itinerary saved successfully!')),
    );
  }

  void _shareItineraryPublicly() {
    final data = _generatedItinerary;
    if (data == null) return;

    final newIt = CreatedItinerary(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title:
          "Roadtrip from ${data['from']} to ${data['to']}",
      from: data['from'],
      to: data['to'],
      days: data['days'],
      travelers: data['travelers'],
      budget: data['budget'],
      pace: _pace,
      diet: _diet,
      author: UserSession.loggedInUser ?? 'Explorer',
      isPublic: true,
      likes: 0,
      itinerary: data['itinerary'],
      orderedWaypoints:
          List.from(data['orderedWaypoints']),
      routePoints: List.from(_itineraryRoutePoints),
      distanceKm: _itineraryDistance ?? 0.0,
      durationMinutes: _itineraryDuration ?? 0.0,
    );

    setState(() {
      UserSession.publicItineraries.add(newIt);
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
          content: Text(
              'Published to Community Itineraries!')),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_generatedItinerary != null) {
      return _buildItineraryResult();
    }
    return Scaffold(
      backgroundColor: kCream,
      body: _buildForm(),
      floatingActionButton: FloatingActionButton(
        onPressed: _openAiChatSheet,
        backgroundColor: kOrange,
        elevation: 6,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16)),
        child: const Icon(Icons.assistant,
            color: Colors.white),
      ),
    );
  }

  Widget _buildForm() {
    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
                20,
                MediaQuery.of(context).padding.top +
                    20,
                20,
                0),
            child: Column(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                Text('AI PLANNER',
                    style: Theme.of(context)
                        .textTheme
                        .labelLarge
                        ?.copyWith(
                            color: kOrange,
                            letterSpacing: 1.5)),
                const SizedBox(height: 6),
                Text('The route adapts\nas you travel.',
                    style: Theme.of(context)
                        .textTheme
                        .displayMedium),
                const SizedBox(height: 4),
                Text(
                    "We'll craft a route that adapts to weather, traffic and your pace.",
                    style: Theme.of(context)
                        .textTheme
                        .bodyMedium),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
        SliverPadding(
          padding:
              const EdgeInsets.symmetric(horizontal: 20),
          sliver: SliverList(
            delegate: SliverChildListDelegate([
              Row(children: [
                Expanded(
                    child: _formCard(
                        label: 'FROM',
                        child: _cityPicker(_from,
                            (v) => setState(() => _from = v)))),
                const SizedBox(width: 12),
                Expanded(
                    child: _formCard(
                        label: 'TO',
                        child: _cityPicker(_to,
                            (v) => setState(() => _to = v)))),
              ]),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(
                    child: _formCard(
                  label: 'DATES',
                  child: GestureDetector(
                    onTap: _pickDateRange,
                    child: Text(
                      _dateRange == null
                          ? 'Select dates'
                          : '${_monthName(_dateRange!.start.month)} ${_dateRange!.start.day} — ${_dateRange!.end.day}',
                      style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight:
                              FontWeight.w600,
                          color: kDark),
                    ),
                  ),
                )),
                const SizedBox(width: 12),
                Expanded(
                    child: _formCard(
                  label: 'TRAVELERS',
                  child:
                      Row(children: [
                    GestureDetector(
                      onTap: () => setState(() =>
                          _travelers =
                              (_travelers - 1)
                                  .clamp(1, 20)),
                      child: Container(
                          width: 28,
                          height: 28,
                          decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              border: Border.all(
                                  color: kBorder)),
                          child: const Icon(
                              Icons.remove,
                              size: 14)),
                    ),
                    const SizedBox(width: 8),
                    Text(
                        '$_travelers ${_travelers == 1 ? 'adult' : 'adults'}',
                        style: GoogleFonts.inter(
                            fontSize: 14,
                            fontWeight:
                                FontWeight.w600,
                            color: kDark)),
                    const SizedBox(width: 8),
                    GestureDetector(
                      onTap: () => setState(
                          () => _travelers++),
                      child: Container(
                          width: 28,
                          height: 28,
                          decoration:
                              const BoxDecoration(
                                  shape:
                                      BoxShape.circle,
                                  color: kDark),
                          child: const Icon(
                              Icons.add,
                              size: 14,
                              color: Colors.white)),
                    ),
                  ]),
                )),
              ]),
              const SizedBox(height: 20),
              _sectionLabel(
                  'PREFERRED TRAVEL TIME'),
              const SizedBox(height: 10),
              _segmentedChoice(
                  _travelTimes,
                  _travelTime,
                  (v) => setState(
                      () => _travelTime = v)),
              const SizedBox(height: 20),
              Row(children: [
                Expanded(
                    child: _formCard(
                  label: 'STAY',
                  child: Column(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,
                    children: [
                      Text(
                          'Rs ${_stayBudget.toInt()}/night',
                          style: GoogleFonts.inter(
                              fontSize: 15,
                              fontWeight:
                                  FontWeight.w600,
                              color: kDark)),
                      Slider(
                          value: _stayBudget,
                          min: 500,
                          max: 20000,
                          divisions: 39,
                          activeColor: kOrange,
                          onChanged: (v) =>
                              setState(() =>
                                  _stayBudget =
                                      v)),
                    ],
                  ),
                )),
                const SizedBox(width: 12),
                Expanded(
                    child: _formCard(
                  label: 'FOOD',
                  child: Column(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,
                    children: [
                      Text(
                          'Rs ${_foodBudget.toInt()}/day',
                          style: GoogleFonts.inter(
                              fontSize: 15,
                              fontWeight:
                                  FontWeight.w600,
                              color: kDark)),
                      Slider(
                          value: _foodBudget,
                          min: 200,
                          max: 5000,
                          divisions: 24,
                          activeColor: kOrange,
                          onChanged: (v) =>
                              setState(() =>
                                  _foodBudget =
                                      v)),
                    ],
                  ),
                )),
              ]),
              const SizedBox(height: 20),
              _sectionLabel('DIET'),
              const SizedBox(height: 10),
              _segmentedChoice(
                  _dietOptions,
                  _diet,
                  (v) => setState(
                      () => _diet = v)),
              const SizedBox(height: 20),
              _sectionLabel('INTERESTS'),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _interestOptions
                    .map((opt) {
                  final active =
                      _interests.contains(opt);
                  return GestureDetector(
                    onTap: () => setState(() =>
                        active
                            ? _interests
                                .remove(opt)
                            : _interests
                                .add(opt)),
                    child: AnimatedContainer(
                      duration: const Duration(
                          milliseconds: 180),
                      padding:
                          const EdgeInsets.symmetric(
                              horizontal: 14,
                              vertical: 8),
                      decoration: BoxDecoration(
                        color: active
                            ? kOrange
                            : Colors.white,
                        borderRadius:
                            BorderRadius.circular(
                                20),
                        border: Border.all(
                            color: active
                                ? kOrange
                                : kBorder),
                      ),
                      child: Text(opt,
                          style: GoogleFonts.inter(
                              fontSize: 13,
                              fontWeight:
                                  FontWeight
                                      .w500,
                              color: active
                                  ? Colors.white
                                  : kDark)),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 20),
              _sectionLabel('PACE'),
              const SizedBox(height: 10),
              _segmentedChoice(
                  _paceOptions,
                  _pace,
                  (v) => setState(
                      () => _pace = v)),
              const SizedBox(height: 28),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _isGenerating
                      ? null
                      : _generateItinerary,
                  icon: _isGenerating
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child:
                              CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color:
                                      Colors.white))
                      : const Icon(
                          Icons.auto_awesome,
                          size: 20),
                  label: Text(_isGenerating
                      ? 'Generating...'
                      : 'Generate itinerary'),
                  style: ElevatedButton.styleFrom(
                    padding:
                        const EdgeInsets.symmetric(
                            vertical: 16),
                    textStyle: GoogleFonts.inter(
                        fontSize: 16,
                        fontWeight:
                            FontWeight.w700),
                  ),
                ),
              ),
              const SizedBox(height: 100),
            ]),
          ),
        ),
      ],
    );
  }

  Widget _buildItineraryResult() {
    final data = _generatedItinerary!;
    final itinerary =
        data['itinerary'] as Map<String, List<Map<String, dynamic>>>;
    final waypoints =
        data['orderedWaypoints'] as List<Place>;
    
    debugPrint('Building itinerary result with ${waypoints.length} waypoints');
    for (var wp in waypoints) {
      debugPrint('Waypoint: ${wp.name} (${wp.safeLatitude}, ${wp.safeLongitude})');
    }

    return Scaffold(
      backgroundColor: kCream,
      appBar: AppBar(
        backgroundColor: kCream,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back,
              color: kDark),
          onPressed: () => setState(
              () => _generatedItinerary = null),
        ),
        title: Text('Your Route & Stops',
            style: GoogleFonts.inter(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: kDark)),
        actions: [
          IconButton(
            icon: const Icon(Icons.save_outlined,
                color: kOrange),
            tooltip: 'Save Trip',
            onPressed: _saveItinerary,
          ),
          IconButton(
            icon: const Icon(Icons.share,
                color: kOrange),
            tooltip: 'Publish Publicly',
            onPressed: _shareItineraryPublicly,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Container(
            height: 260,
            margin: const EdgeInsets.only(bottom: 20),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: kBorder),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(19),
              child: Stack(
                children: [
                  FlutterMap(
                    options: MapOptions(
                      initialCenter:
                          _getCityCoords(_from),
                      initialZoom: 7.5,
                      onTap: (_, _) => setState(() =>
                          _selectedItineraryPlace =
                              null),
                    ),
                    children: [
                      TileLayer(
                        urlTemplate:
                            'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        userAgentPackageName:
                            'com.yatrasathi.app',
                      ),
                      RichAttributionWidget(
                        attributions: [
                          TextSourceAttribution(
                            'OpenStreetMap contributors',
                            onTap: () {},
                          ),
                        ],
                      ),
                      // OSRM base route (blue, thinner)
                      if (_osrmRoutePoints.isNotEmpty)
                        PolylineLayer(
                          polylines: <Polyline<Object>>[
                            Polyline(
                              points: _osrmRoutePoints,
                              color: Colors.blue.withValues(alpha: 0.5),
                              strokeWidth: 3,
                            ),
                          ],
                        ),
                      // Itinerary route (orange, thicker - overrides OSRM where waypoints exist)
                      if (_itineraryRoutePoints.isNotEmpty)
                        PolylineLayer(
                          polylines: <Polyline<
                              Object>>[
                            Polyline(
                              points:
                                  _itineraryRoutePoints,
                              color: kOrange,
                              strokeWidth: 5,
                            ),
                          ],
                        ),
                      MarkerLayer(markers: [
                        ...waypoints.map((wp) {
                          final isStartEnd = wp.id ==
                                  'start' ||
                              wp.id == 'end';
                          final selected =
                              _selectedItineraryPlace
                                      ?.id ==
                                  wp.id;
                          debugPrint('Creating marker for ${wp.name} at (${wp.safeLatitude}, ${wp.safeLongitude})');
                          return Marker(
                            point: LatLng(
                                wp.safeLatitude,
                                wp.safeLongitude),
                            width: selected
                                ? 48
                                : (isStartEnd
                                    ? 42
                                    : 32),
                            height: selected
                                ? 48
                                : (isStartEnd
                                    ? 42
                                    : 32),
                            child: GestureDetector(
                              onTap: () =>
                                  setState(() =>
                                      _selectedItineraryPlace =
                                          wp),
                              child: Tooltip(
                                message:
                                    '${wp.name}\n${wp.category}',
                                child: Container(
                                  decoration:
                                      BoxDecoration(
                                    color: selected
                                        ? Colors
                                            .white
                                        : (isStartEnd
                                            ? kDark
                                            : kOrange),
                                    shape: BoxShape
                                        .circle,
                                    border: Border.all(
                                        color: selected
                                            ? kOrange
                                            : Colors
                                                .white,
                                        width: 2),
                                    boxShadow: const [
                                      BoxShadow(
                                          color: Colors
                                              .black26,
                                          blurRadius:
                                              4,
                                          offset: Offset(
                                              0,
                                              2))
                                    ],
                                  ),
                                  child: Icon(
                                    wp.id == 'start'
                                        ? Icons
                                            .play_arrow
                                        : wp.id ==
                                                'end'
                                            ? Icons
                                                .flag
                                            : Icons
                                                .location_on,
                                    size: isStartEnd
                                        ? 18
                                        : 14,
                                    color: selected
                                        ? kOrange
                                        : Colors
                                            .white,
                                  ),
                                ),
                              ),
                            ),
                          );
                        }),
                      ]),
                      // Nearby POI overlay (smaller, semi-transparent markers)
                      if (_nearbyPois.isNotEmpty)
                        MarkerLayer(markers: [
                          ..._nearbyPois.map((poi) {
                            // Skip if this POI is already in the selected waypoints
                            final isInWaypoints = waypoints.any((wp) => wp.id == poi.id);
                            if (isInWaypoints) return null;
                            
                            return Marker(
                              point: LatLng(poi.safeLatitude, poi.safeLongitude),
                              width: 24,
                              height: 24,
                              child: Container(
                                decoration: BoxDecoration(
                                  color: Colors.grey.withValues(alpha: 0.5),
                                  shape: BoxShape.circle,
                                  border: Border.all(color: Colors.white, width: 1),
                                ),
                                child: const Icon(
                                  Icons.location_on,
                                  color: Colors.white,
                                  size: 12,
                                ),
                              ),
                            );
                          }).where((m) => m != null).cast<Marker>(),
                        ]),
                    ],
                  ),
                  if (_isItineraryRouteLoading)
                    Positioned.fill(
                      child: Container(
                        color: Colors.black26,
                        child: const Center(
                          child: CircularProgressIndicator(
                            color: kOrange,
                          ),
                        ),
                      ),
                    ),
                  if (_selectedItineraryPlace != null)
                    Positioned(
                      bottom: 12,
                      left: 12,
                      right: 12,
                      child: Card(
                        elevation: 6,
                        shape:
                            RoundedRectangleBorder(
                          borderRadius:
                              BorderRadius.circular(
                                  16),
                        ),
                        child: Padding(
                          padding:
                              const EdgeInsets.all(
                                  12),
                          child: Column(
                            mainAxisSize:
                                MainAxisSize.min,
                            crossAxisAlignment:
                                CrossAxisAlignment
                                    .start,
                            children: [
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment
                                        .spaceBetween,
                                children: [
                                  Expanded(
                                    child: Text(
                                      _selectedItineraryPlace!
                                          .name,
                                      style: GoogleFonts.inter(
                                          fontWeight:
                                              FontWeight.bold,
                                          fontSize:
                                              14,
                                          color:
                                              kDark),
                                      maxLines: 1,
                                      overflow:
                                          TextOverflow.ellipsis,
                                    ),
                                  ),
                                  GestureDetector(
                                    onTap: () =>
                                        setState(() =>
                                            _selectedItineraryPlace =
                                                null),
                                    child: const Icon(
                                        Icons.close,
                                        size: 18,
                                        color:
                                            kGray),
                                  ),
                                ],
                              ),
                              const SizedBox(
                                  height: 2),
                              Text(
                                _selectedItineraryPlace!
                                    .category,
                                style: GoogleFonts.inter(
                                    color: kOrange,
                                    fontSize: 11,
                                    fontWeight:
                                        FontWeight
                                            .w600),
                              ),
                              if (_selectedItineraryPlace!
                                  .safeDescription
                                  .isNotEmpty) ...[
                                const SizedBox(
                                    height: 6),
                                Text(
                                  _selectedItineraryPlace!
                                      .safeDescription,
                                  style: GoogleFonts.inter(
                                      color: kGray,
                                      fontSize: 11),
                                  maxLines: 2,
                                  overflow:
                                      TextOverflow
                                          .ellipsis,
                                ),
                              ],
                              if (_selectedItineraryPlace!.id !=
                                      'start' &&
                                  _selectedItineraryPlace!
                                          .id !=
                                      'end') ...[
                                const SizedBox(
                                    height: 6),
                                Align(
                                  alignment:
                                      Alignment
                                          .centerRight,
                                  child: TextButton(
                                    style: TextButton
                                        .styleFrom(
                                      padding:
                                          EdgeInsets
                                              .zero,
                                      minimumSize:
                                          Size.zero,
                                      tapTargetSize:
                                          MaterialTapTargetSize
                                              .shrinkWrap,
                                    ),
                                    onPressed:
                                        () {
                                      Navigator.push(
                                          context,
                                          MaterialPageRoute(
                                              builder: (_) => PlaceDetailScreen(place: _selectedItineraryPlace!)));
                                    },
                                    child: Text(
                                        'View Details',
                                        style: GoogleFonts.inter(
                                            fontWeight: FontWeight
                                                .bold,
                                            color:
                                                kOrange,
                                            fontSize:
                                                12)),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),
                  if (_isItineraryRouteLoading)
                    Container(
                      color: Colors.black26,
                      child: const Center(
                          child:
                              CircularProgressIndicator(
                                  color: kOrange)),
                    ),
                ],
              ),
            ),
          ),
          if (_itineraryDistance != null) ...[
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 16, vertical: 12),
              margin:
                  const EdgeInsets.only(bottom: 20),
              decoration: BoxDecoration(
                color:
                    kOrange.withValues(alpha: 0.08),
                borderRadius:
                    BorderRadius.circular(14),
                border: Border.all(
                    color: kOrange
                        .withValues(alpha: 0.2)),
              ),
              child: Row(
                mainAxisAlignment:
                    MainAxisAlignment.spaceAround,
                children: [
                  Column(children: [
                    Text('TOTAL DISTANCE',
                        style: GoogleFonts.inter(
                            fontSize: 10,
                            fontWeight:
                                FontWeight.bold,
                            color: kGray)),
                    const SizedBox(height: 4),
                    Text(
                        '${_itineraryDistance!.toStringAsFixed(1)} km',
                        style: GoogleFonts.inter(
                            fontSize: 16,
                            fontWeight:
                                FontWeight.bold,
                            color: kDark)),
                  ]),
                  Column(children: [
                    Text('DRIVE TIME',
                        style: GoogleFonts.inter(
                            fontSize: 10,
                            fontWeight:
                                FontWeight.bold,
                            color: kGray)),
                    const SizedBox(height: 4),
                    Text(
                        '${(_itineraryDuration! / 60).toStringAsFixed(1)} hrs',
                        style: GoogleFonts.inter(
                            fontSize: 16,
                            fontWeight:
                                FontWeight.bold,
                            color: kDark)),
                  ]),
                ],
              ),
            ),
          ],
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: kOrange,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                Text(
                    "${data['from']} → ${data['to']}",
                    style: GoogleFonts.playfairDisplay(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                        fontStyle:
                            FontStyle.italic)),
                const SizedBox(height: 8),
                Row(children: [
                  _badge("${data['days']} days"),
                  const SizedBox(width: 8),
                  _badge(
                      "${data['travelers']} travelers"),
                  const SizedBox(width: 8),
                  _badge(data['budget']),
                ]),
                const SizedBox(height: 6),
                Text(
                    'Pace: $_pace · $_diet · ${_interests.take(2).join(', ')}',
                    style: GoogleFonts.inter(
                        fontSize: 12,
                        color: Colors.white70)),
              ],
            ),
          ),
          const SizedBox(height: 24),
          ...itinerary.entries.map((entry) =>
              DaySection(
                  day: entry.key,
                  stops: entry.value)),
          const SizedBox(height: 80),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _openAiChatSheet,
        backgroundColor: kOrange,
        elevation: 6,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16)),
        child: const Icon(Icons.assistant,
            color: Colors.white),
      ),
    );
  }

  Widget _badge(String label) => Container(
        padding: const EdgeInsets.symmetric(
            horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.25),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(label,
            style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Colors.white)),
      );

  Widget _formCard(
          {required String label,
          required Widget child}) =>
      Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: kCardBg,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: kBorder),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(label,
                style: Theme.of(context)
                    .textTheme
                    .labelLarge),
            const SizedBox(height: 6),
            child,
          ],
        ),
      );

  Widget _cityPicker(
          String current,
          ValueChanged<String> onChange) =>
      DropdownButton<String>(
        value: current,
        isExpanded: true,
        underline: const SizedBox.shrink(),
        style: GoogleFonts.inter(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            color: kDark),
        items: _nepalCities
            .map((c) => DropdownMenuItem(
                value: c, child: Text(c)))
            .toList(),
        onChanged: (v) {
          if (v != null) onChange(v);
        },
      );

  Widget _sectionLabel(String label) => Text(label,
      style: Theme.of(context)
          .textTheme
          .labelLarge
          ?.copyWith(fontSize: 11));

  Widget _segmentedChoice(
          List<String> options,
          String selected,
          ValueChanged<String> onChange) =>
      Row(
        children: options.map((opt) {
          final active = opt == selected;
          return Expanded(
            child: GestureDetector(
              onTap: () => onChange(opt),
              child: AnimatedContainer(
                duration:
                    const Duration(milliseconds: 200),
                margin: EdgeInsets.only(
                    right: opt != options.last
                        ? 8
                        : 0),
                padding: const EdgeInsets.symmetric(
                    vertical: 10),
                decoration: BoxDecoration(
                  color: active ? kDark : Colors.white,
                  borderRadius:
                      BorderRadius.circular(10),
                  border: Border.all(
                      color: active ? kDark : kBorder),
                ),
                child: Text(opt,
                    textAlign: TextAlign.center,
                    style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: active
                            ? Colors.white
                            : kDark)),
              ),
            ),
          );
        }).toList(),
      );

  Future<void> _pickDateRange() async {
    final now = DateTime.now();
    final range = await showDateRangePicker(
      context: context,
      firstDate: now,
      lastDate: now.add(const Duration(days: 365)),
      initialDateRange: _dateRange ??
          DateTimeRange(
              start: now.add(const Duration(days: 7)),
              end: now.add(const Duration(days: 10))),
      builder: (ctx, child) => Theme(
        data: Theme.of(ctx).copyWith(
            colorScheme: const ColorScheme.light(
                primary: kOrange,
                onPrimary: Colors.white)),
        child: child!,
      ),
    );
    if (range != null)
      setState(() => _dateRange = range);
  }
}