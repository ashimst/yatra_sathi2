import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/services/route_service.dart';
import 'package:mobile/widgets/placeholder_image.dart';
import 'package:mobile/screens/place_detail_screen.dart';

class MapScreen extends StatefulWidget {
  final List<Place> places;
  final VoidCallback onBack;

  const MapScreen({
    super.key,
    required this.places,
    required this.onBack,
  });

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final MapController _mapController = MapController();
  Place? _selectedPlace;
  List<LatLng> _routePoints = [];
  double? _routeDistance, _routeDuration;
  bool _isRoutingLoading = false;
  final LatLng _ktm = const LatLng(27.7172, 85.3240);
  final RouteService _routeService = RouteService();

  Color _markerColor(String? cat) {
    switch (cat?.toLowerCase()) {
      case 'hindu temple':
      case 'buddhist temple':
      case 'place of worship':
      case 'pilgrimage place':
        return const Color(0xFFFF9800);
      case 'mountain range':
      case 'mountain peak':
      case 'hiking area':
        return const Color(0xFFE53935);
      case 'museum':
      case 'historical landmark':
        return const Color(0xFF7B1FA2);
      case 'lake':
      case 'river':
      case 'nature preserve':
      case 'national park':
        return const Color(0xFF2E7D32);
      case 'park':
      case 'campground':
        return const Color(0xFF43A047);
      default:
        return kOrange;
    }
  }

  IconData _markerIcon(String? cat) {
    switch (cat?.toLowerCase()) {
      case 'hindu temple':
      case 'buddhist temple':
      case 'place of worship':
      case 'pilgrimage place':
        return Icons.temple_hindu;
      case 'mountain range':
      case 'mountain peak':
        return Icons.terrain;
      case 'hiking area':
        return Icons.directions_walk;
      case 'museum':
      case 'historical landmark':
        return Icons.account_balance;
      case 'lake':
      case 'river':
        return Icons.water;
      case 'national park':
      case 'nature preserve':
        return Icons.park;
      case 'church':
      case 'religious institution':
        return Icons.church;
      case 'campground':
        return Icons.cabin;
      default:
        return Icons.location_on;
    }
  }

  Future<void> _getRoute(Place dest) async {
    setState(() {
      _isRoutingLoading = true;
      _routePoints = [];
      _routeDistance = null;
      _routeDuration = null;
    });
    
    try {
      debugPrint('Fetching route to ${dest.name}');
      final data = await _routeService.getRoute(
          _ktm, LatLng(dest.safeLatitude, dest.safeLongitude));
      debugPrint('Route data received: ${data.keys}');
      
      final geometry = data['geometry'];
      if (geometry != null && geometry['coordinates'] != null) {
        final coords = geometry['coordinates'] as List;
        debugPrint('Processing ${coords.length} route coordinates');
        
        setState(() {
          _routePoints = coords
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
          _routeDistance =
              (data['distance_km'] as num?)?.toDouble();
          _routeDuration =
              (data['duration_minutes'] as num?)
                  ?.toDouble();
        });
        
        debugPrint('Route loaded: ${_routePoints.length} points, ${_routeDistance}km');
        
        if (_routePoints.isNotEmpty) {
          _mapController.fitCamera(CameraFit.bounds(
            bounds: LatLngBounds.fromPoints([
              _ktm,
              LatLng(dest.safeLatitude, dest.safeLongitude),
              ..._routePoints
            ]),
            padding: const EdgeInsets.all(60),
          ));
        }
      } else {
        debugPrint('Invalid geometry in route response');
        if (mounted)
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
                content: Text(
                    'Route data was empty. Try again.')),
          );
      }
    } catch (e) {
      debugPrint('Route error: $e');
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Route service unavailable. ${e.toString().split(":").last.trim()}')),
        );
    } finally {
      if (mounted)
        setState(() => _isRoutingLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter:
                  const LatLng(28.3949, 84.1240),
              initialZoom: 7.0,
              onTap: (_, _) => setState(() {
                _selectedPlace = null;
                _routePoints = [];
              }),
            ),
            children: [
              TileLayer(
                urlTemplate:
                    'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName:
                    'com.yatrasathi.app',
              ),
              if (_routePoints.isNotEmpty)
                PolylineLayer(
                  polylines: <Polyline<Object>>[
                    Polyline(
                      points: _routePoints,
                      color: kOrange,
                      strokeWidth: 5,
                    ),
                  ],
                ),
              MarkerLayer(markers: [
                Marker(
                  point: _ktm,
                  width: 44,
                  height: 44,
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.blue
                          .withValues(alpha: 0.2),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                        Icons.my_location,
                        color: Colors.blue,
                        size: 26),
                  ),
                ),
                ...widget.places.map((p) {
                  final selected =
                      _selectedPlace?.id == p.id;
                  final color = _markerColor(p.category);
                  return Marker(
                    point: LatLng(
                        p.safeLatitude, p.safeLongitude),
                    width: selected ? 52 : 40,
                    height: selected ? 52 : 40,
                    child: GestureDetector(
                      onTap: () {
                        setState(
                            () => _selectedPlace = p);
                        _mapController.move(
                            LatLng(p.safeLatitude - 0.04,
                                p.safeLongitude),
                            12.0);
                      },
                      child: AnimatedContainer(
                        duration: const Duration(
                            milliseconds: 200),
                        decoration: BoxDecoration(
                          color: selected
                              ? Colors.white
                              : color,
                          shape: BoxShape.circle,
                          border: Border.all(
                              color: Colors.white,
                              width: 2),
                          boxShadow: const [
                            BoxShadow(
                                color: Colors.black26,
                                blurRadius: 6,
                                offset:
                                    Offset(0, 3))
                          ],
                        ),
                        child: Icon(
                            _markerIcon(
                                p.category),
                            color: selected
                                ? color
                                : Colors.white,
                            size: selected ? 26 : 18),
                      ),
                    ),
                  );
                }),
              ]),
            ],
          ),
          Positioned(
            top: MediaQuery.of(context).padding.top + 12,
            left: 16,
            child: GestureDetector(
              onTap: widget.onBack,
              child: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius:
                      BorderRadius.circular(12),
                  border: Border.all(color: kBorder),
                  boxShadow: const [
                    BoxShadow(
                        color: Colors.black12,
                        blurRadius: 4)
                  ],
                ),
                child: const Icon(Icons.arrow_back,
                    color: kDark, size: 20),
              ),
            ),
          ),
          if (_selectedPlace != null)
            Positioned(
              left: 12,
              right: 12,
              bottom: 16,
              child: _buildDetailCard(_selectedPlace!),
            ),
        ],
      ),
    );
  }

  Widget _buildDetailCard(Place place) {
    return Container(
      decoration: BoxDecoration(
        color: kCardBg,
        borderRadius: BorderRadius.circular(20),
        boxShadow: const [
          BoxShadow(
              color: Colors.black12,
              blurRadius: 16,
              offset: Offset(0, -4))
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              ClipRRect(
                borderRadius:
                    BorderRadius.circular(12),
                child: place.imageUrl.isNotEmpty
                    ? Image.network(place.imageUrl,
                        width: 72,
                        height: 72,
                        fit: BoxFit.cover,
                        errorBuilder: (c, e, s) =>
                            buildPlaceholderImage(
                                place.category))
                    : buildPlaceholderImage(
                        place.category),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment:
                      CrossAxisAlignment.start,
                  children: [
                    Text(place.name,
                        style: GoogleFonts.inter(
                            fontSize: 16,
                            fontWeight:
                                FontWeight.w700,
                            color: kDark)),
                    const SizedBox(height: 2),
                    Text(
                        '${place.category} · ${place.safeDistrict}',
                        style: GoogleFonts.inter(
                            fontSize: 12,
                            color: kGray)),
                    const SizedBox(height: 6),
                    Row(children: [
                      const Icon(Icons.star,
                          size: 14,
                          color: kOrange),
                      const SizedBox(width: 3),
                      Text(
                          place.safeRating
                              .toStringAsFixed(1),
                          style: GoogleFonts.inter(
                              fontSize: 13,
                              fontWeight:
                                  FontWeight.w600,
                              color: kDark)),
                    ]),
                  ],
                ),
              ),
              IconButton(
                onPressed: () => setState(() {
                  _selectedPlace = null;
                  _routePoints = [];
                }),
                icon: const Icon(Icons.close,
                    color: kGray),
              ),
            ],
          ),
          if (_routeDistance != null) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color:
                    kOrange.withValues(alpha: 0.08),
                borderRadius:
                    BorderRadius.circular(10),
                border: Border.all(
                    color: kOrange
                        .withValues(alpha: 0.3)),
              ),
              child: Row(
                mainAxisAlignment:
                    MainAxisAlignment.spaceAround,
                children: [
                  Row(children: [
                    const Icon(
                        Icons.directions_car,
                        color: kOrange,
                        size: 16),
                    const SizedBox(width: 4),
                    Text(
                        '${_routeDistance!.toStringAsFixed(0)} km',
                        style: GoogleFonts.inter(
                            fontWeight:
                                FontWeight.w700,
                            color: kDark,
                            fontSize: 13)),
                  ]),
                  Row(children: [
                    const Icon(
                        Icons.timer_outlined,
                        color: kOrange,
                        size: 16),
                    const SizedBox(width: 4),
                    Text(
                        '${_routeDuration!.toStringAsFixed(0)} mins',
                        style: GoogleFonts.inter(
                            fontWeight:
                                FontWeight.w700,
                            color: kDark,
                            fontSize: 13)),
                  ]),
                ],
              ),
            ),
          ],
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: ElevatedButton.icon(
                onPressed: _isRoutingLoading
                    ? null
                    : () => _getRoute(place),
                icon: _isRoutingLoading
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white))
                    : const Icon(
                        Icons.navigation_outlined,
                        size: 18),
                label: Text(_routeDistance != null
                    ? 'Reroute'
                    : 'Route from KTM'),
              ),
            ),
            const SizedBox(width: 8),
            OutlinedButton(
              onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                      builder: (_) =>
                          PlaceDetailScreen(
                              place: place))),
              style: OutlinedButton.styleFrom(
                foregroundColor: kDark,
                side: const BorderSide(
                    color: kBorder),
                shape: RoundedRectangleBorder(
                    borderRadius:
                        BorderRadius.circular(12)),
                padding: const EdgeInsets.symmetric(
                    horizontal: 14, vertical: 14),
              ),
              child: Text('Details',
                  style: GoogleFonts.inter(
                      fontWeight:
                          FontWeight.w600)),
            ),
          ]),
        ],
      ),
    );
  }
}