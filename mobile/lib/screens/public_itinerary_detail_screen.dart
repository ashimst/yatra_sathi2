import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/created_itinerary.dart';
import 'package:mobile/services/user_session.dart';
import 'package:mobile/screens/place_detail_screen.dart';
import 'package:mobile/widgets/day_section.dart';
import 'package:mobile/models/place.dart';

class PublicItineraryDetailScreen extends StatefulWidget {
  final CreatedItinerary itinerary;
  const PublicItineraryDetailScreen({
    super.key,
    required this.itinerary,
  });

  @override
  State<PublicItineraryDetailScreen> createState() =>
      _PublicItineraryDetailScreenState();
}

class _PublicItineraryDetailScreenState
    extends State<PublicItineraryDetailScreen> {
  Place? _selectedItineraryPlace;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kCream,
      appBar: AppBar(
        backgroundColor: kCream,
        elevation: 0,
        title: Text(widget.itinerary.title,
            style: GoogleFonts.inter(
                fontSize: 16,
                fontWeight: FontWeight.bold)),
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
                      initialCenter: LatLng(
                          widget.itinerary.orderedWaypoints
                              .first.safeLatitude,
                          widget.itinerary.orderedWaypoints
                              .first.safeLongitude),
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
                      if (widget.itinerary.routePoints
                          .isNotEmpty)
                        PolylineLayer(
                          polylines: <Polyline<
                              Object>>[
                            Polyline(
                              points: widget
                                  .itinerary
                                  .routePoints,
                              color: kOrange,
                              strokeWidth: 5,
                            ),
                          ],
                        ),
                      MarkerLayer(markers: [
                        ...widget.itinerary.orderedWaypoints
                            .map((wp) {
                          final isStartEnd = wp.id ==
                                  'start' ||
                              wp.id == 'end';
                          final selected =
                              _selectedItineraryPlace
                                      ?.id ==
                                  wp.id;
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
                    ],
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
                ],
              ),
            ),
          ),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.copy),
                  label: const Text(
                      'Clone & Customize'),
                  onPressed: () {
                    // Clone to saved itineraries
                    final clone = CreatedItinerary(
                      id: DateTime.now()
                          .millisecondsSinceEpoch
                          .toString(),
                      title:
                          'Copy of ${widget.itinerary.title}',
                      from: widget.itinerary.from,
                      to: widget.itinerary.to,
                      days: widget.itinerary.days,
                      travelers:
                          widget.itinerary.travelers,
                      budget: widget.itinerary.budget,
                      pace: widget.itinerary.pace,
                      diet: widget.itinerary.diet,
                      author:
                          UserSession.loggedInUser ??
                              'Explorer',
                      itinerary: Map.from(widget
                          .itinerary.itinerary),
                      orderedWaypoints: List.from(
                          widget.itinerary
                              .orderedWaypoints),
                      routePoints: List.from(
                          widget.itinerary.routePoints),
                      distanceKm:
                          widget.itinerary.distanceKm,
                      durationMinutes: widget
                          .itinerary.durationMinutes,
                    );
                    UserSession.savedItineraries
                        .add(clone);
                    ScaffoldMessenger.of(context)
                        .showSnackBar(
                      const SnackBar(
                          content: Text(
                              'Cloned to your Saved Roadtrips! You can now edit it.')),
                    );
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          ...widget.itinerary.itinerary.entries.map(
              (entry) => DaySection(
                  day: entry.key,
                  stops: entry.value)),
        ],
      ),
    );
  }
}