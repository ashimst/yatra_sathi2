import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/created_itinerary.dart';
import 'package:mobile/screens/place_detail_screen.dart';
import 'package:mobile/widgets/day_section.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/services/ai_service.dart';
import 'package:mobile/services/user_session.dart';
import 'package:mobile/widgets/ai_chat_widget.dart';
class SavedItineraryDetailScreen extends StatefulWidget {
  final CreatedItinerary itinerary;
  const SavedItineraryDetailScreen({
    super.key,
    required this.itinerary,
  });

  @override
  State<SavedItineraryDetailScreen> createState() =>
      _SavedItineraryDetailScreenState();
}

class _SavedItineraryDetailScreenState
    extends State<SavedItineraryDetailScreen> {
  late TextEditingController _titleController;
  bool _isEditing = false;
  Place? _selectedItineraryPlace;
  
  // AI editing workflow state variables
  CreatedItinerary? _proposedItinerary; // Stores the AI-proposed edited itinerary
  bool _isEditingWithAI = false; // Tracks if AI editing workflow is active
  bool _isFetchingProposal = false; // Loading state while fetching proposed changes

  @override
  void initState() {
    super.initState();
    _titleController = TextEditingController(
        text: widget.itinerary.title);
  }

  @override
  void dispose() {
    _titleController.dispose();
    super.dispose();
  }
  
  /// Opens a dialog for the user to enter an editing request for AI
  void _showEditRequestDialog() {
    final TextEditingController editController = TextEditingController();
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Edit with AI', style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Describe the changes you want to make to your itinerary:',
              style: GoogleFonts.inter(fontSize: 13, color: kGray),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: editController,
              maxLines: 3,
              decoration: InputDecoration(
                hintText: 'e.g., "Replace the museum with a hiking trail"',
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                contentPadding: const EdgeInsets.all(12),
              ),
              style: GoogleFonts.inter(fontSize: 14),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel', style: GoogleFonts.inter(color: kGray)),
          ),
          ElevatedButton(
            onPressed: () {
              final editRequest = editController.text.trim();
              if (editRequest.isNotEmpty) {
                Navigator.pop(context);
                _fetchProposedEdits(editRequest);
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: kOrange),
            child: Text('Generate Proposal', style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }
  
  /// Fetches proposed edits from the AI service based on user's edit request
  Future<void> _fetchProposedEdits(String editRequest) async {
    setState(() => _isFetchingProposal = true);

    try {
      // Convert current itinerary to JSON format for the backend.
      // Keys are stored in snake_case in the workspace snapshot, so send
      // both snake_case and camelCase versions so the pipeline is
      // resilient to whichever convention the backend uses.
      final currentItineraryJson = <String, dynamic>{
        'id': widget.itinerary.id,
        'title': widget.itinerary.title,
        'from': widget.itinerary.from,
        'origin': widget.itinerary.from,
        'to': widget.itinerary.to,
        'destination': widget.itinerary.to,
        'days': widget.itinerary.days,
        'travelers': widget.itinerary.travelers,
        'budget': widget.itinerary.budget,
        'pace': widget.itinerary.pace,
        'diet': widget.itinerary.diet,
        'author': widget.itinerary.author,
        'likes': widget.itinerary.likes,
        'is_public': widget.itinerary.isPublic,
        'isPublic': widget.itinerary.isPublic,
        'itinerary': widget.itinerary.itinerary,
        'ordered_waypoints': widget.itinerary.orderedWaypoints
            .map((p) => {
                  'id': p.id,
                  'name': p.name,
                  'category': p.category,
                  'district': p.district,
                  'province': p.province,
                  'city': p.city,
                  'description': p.description,
                  'history': p.history,
                  'latitude': p.latitude,
                  'longitude': p.longitude,
                  'images': p.images,
                  'has_ticket': p.hasTicket,
                  'hasTicket': p.hasTicket,
                })
            .toList(),
        'orderedWaypoints': widget.itinerary.orderedWaypoints
            .map((p) => {
                  'id': p.id,
                  'name': p.name,
                  'category': p.category,
                  'district': p.district,
                  'province': p.province,
                  'city': p.city,
                  'description': p.description,
                  'history': p.history,
                  'latitude': p.latitude,
                  'longitude': p.longitude,
                  'images': p.images,
                  'hasTicket': p.hasTicket,
                })
            .toList(),
        'route_points': widget.itinerary.routePoints
            .map((ll) => [ll.latitude, ll.longitude]).toList(),
        'routePoints': widget.itinerary.routePoints
            .map((ll) => [ll.latitude, ll.longitude]).toList(),
        'distance_km': widget.itinerary.distanceKm,
        'distanceKm': widget.itinerary.distanceKm,
        'duration_minutes': widget.itinerary.durationMinutes,
        'durationMinutes': widget.itinerary.durationMinutes,
      };

      final String userId = UserSession.loggedInUser ?? 'guest_user';

      final response = await AIService.editItinerary(
        currentItinerary: currentItineraryJson,
        editRequest: editRequest,
        userId: userId,
      );

      // Parse the proposed itinerary from the response
      final proposedData =
          response['proposed_itinerary'] as Map<String, dynamic>? ??
              currentItineraryJson;

      final warnings = List<String>.from(response['warnings'] ?? []);
      final explanation =
          response['explanation']?.toString() ?? 'Proposal generated';

      // Reconstruct the proposed itinerary object
      final proposedItinerary = CreatedItinerary(
        id: (proposedData['id'] ?? widget.itinerary.id).toString(),
        title: (proposedData['title'] ?? widget.itinerary.title).toString(),
        from: (proposedData['from'] ?? proposedData['origin'] ?? widget.itinerary.from)
            .toString(),
        to: (proposedData['to'] ?? proposedData['destination'] ?? widget.itinerary.to)
            .toString(),
        days: (proposedData['days'] as num?)?.toInt() ?? widget.itinerary.days,
        travelers: (proposedData['travelers'] as num?)?.toInt() ??
            widget.itinerary.travelers,
        budget:
            (proposedData['budget'] ?? widget.itinerary.budget).toString(),
        pace: (proposedData['pace'] ?? widget.itinerary.pace).toString(),
        diet: (proposedData['diet'] ?? widget.itinerary.diet).toString(),
        author: (proposedData['author'] ?? widget.itinerary.author).toString(),
        likes: (proposedData['likes'] as num?)?.toInt() ?? widget.itinerary.likes,
        isPublic: (proposedData['is_public'] as bool?) ??
            (proposedData['isPublic'] as bool?) ??
            widget.itinerary.isPublic,
        itinerary: ((proposedData['itinerary'] as Map?) ??
                Map.from(widget.itinerary.itinerary))
            .map(
          (key, value) => MapEntry(
            key.toString(),
            List<Map<String, dynamic>>.from(value ?? []),
          ),
        ),
        orderedWaypoints: ((proposedData['orderedWaypoints'] ??
                    proposedData['ordered_waypoints']) as List?)
                ?.map((p) => Place(
                      id: p['id']?.toString() ?? '',
                      name: p['name']?.toString() ?? '',
                      category: p['category']?.toString() ?? '',
                      district: p['district']?.toString() ?? '',
                      province: p['province']?.toString() ?? '',
                      city: p['city']?.toString() ?? '',
                      description: p['description']?.toString() ?? '',
                      history: p['history']?.toString() ?? '',
                      latitude: (p['latitude'] as num).toDouble(),
                      longitude: (p['longitude'] as num).toDouble(),
                      images: List<String>.from(p['images'] ?? []),
                      hasTicket: (p['hasTicket'] as bool?) ??
                          (p['has_ticket'] as bool?) ??
                          false,
                    ))
                .toList() ??
            widget.itinerary.orderedWaypoints,
        routePoints: ((proposedData['routePoints'] ?? proposedData['route_points'])
                    as List?)
                ?.map((ll) {
              if (ll is List && ll.length >= 2) {
                return LatLng(
                  (ll[0] as num).toDouble(),
                  (ll[1] as num).toDouble(),
                );
              }
              if (ll is Map) {
                return LatLng(
                  (ll['lat'] ?? ll['latitude'] as num).toDouble(),
                  (ll['lng'] ?? ll['longitude'] as num).toDouble(),
                );
              }
              return null;
            }).whereType<LatLng>().toList() ??
            widget.itinerary.routePoints,
        distanceKm: (proposedData['distanceKm'] as num?)?.toDouble() ??
            (proposedData['distance_km'] as num?)?.toDouble() ??
            widget.itinerary.distanceKm,
        durationMinutes: (proposedData['durationMinutes'] as num?)?.toDouble() ??
            (proposedData['duration_minutes'] as num?)?.toDouble() ??
            widget.itinerary.durationMinutes,
      );

      setState(() {
        _proposedItinerary = proposedItinerary;
        _isEditingWithAI = true;
      });

      if (warnings.isNotEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: Colors.orange,
            content: Text('⚠ ${warnings.first}'),
            duration: const Duration(seconds: 4),
          ),
        );
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(explanation)),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to generate proposal: $e')),
      );
    } finally {
      if (mounted) setState(() => _isFetchingProposal = false);
    }
  }
  
  /// Accepts the proposed changes and replaces the current itinerary
  void _acceptChanges() {
    if (_proposedItinerary == null) return;
    
    // Find and replace the itinerary in the session list
    final index = UserSession.savedItineraries.indexWhere(
      (it) => it.id == widget.itinerary.id
    );
    
    if (index != -1) {
      setState(() {
        // Replace the entire itinerary object in the session
        UserSession.savedItineraries[index] = _proposedItinerary!;
        
        // Reset AI editing state
        _proposedItinerary = null;
        _isEditingWithAI = false;
      });
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Changes accepted!')),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Error: Could not find itinerary to update')),
      );
    }
  }
  
  /// Rejects the proposed changes and discards the proposed itinerary
  void _rejectChanges() {
    setState(() {
      _proposedItinerary = null;
      _isEditingWithAI = false;
    });
    
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Changes rejected')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final activeIt = _proposedItinerary ?? widget.itinerary;

    return Scaffold(
      backgroundColor: kCream,
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          showModalBottomSheet(
            context: context,
            isScrollControlled: true,
            backgroundColor: Colors.transparent,
            builder: (context) => AIChatWidget(
              screenContext: 'saved_itinerary_detail',
              itineraryContext: {
                'id': activeIt.id,
                'title': activeIt.title,
                'from': activeIt.from,
                'to': activeIt.to,
                'days': activeIt.days,
                'budget': activeIt.budget,
                'pace': activeIt.pace,
                'itinerary': activeIt.itinerary,
                'distance_km': activeIt.distanceKm,
                'duration_minutes': activeIt.durationMinutes,
              },
              onEditApplied: (args) {
                setState(() {
                  // Refresh state on AI edit approval
                });
              },
            ),
          );
        },
        backgroundColor: kOrange,
        icon: const Icon(Icons.auto_awesome, color: Colors.white),
        label: Text('AI Assistant', style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.bold)),
      ),
      appBar: AppBar(
        backgroundColor: kCream,
        elevation: 0,
        title: _isEditing
            ? TextField(
                controller: _titleController,
                decoration: const InputDecoration(
                    hintText: 'Itinerary Title'),
              )
            : Text(widget.itinerary.title,
                style: GoogleFonts.inter(
                    fontSize: 16,
                    fontWeight: FontWeight.bold)),
        actions: [
          // Edit with AI button
          if (!_isEditingWithAI)
            IconButton(
              icon: const Icon(Icons.auto_awesome, color: kOrange),
              tooltip: 'Edit with AI',
              onPressed: _showEditRequestDialog,
            ),
          // Regular edit button
          IconButton(
            icon: Icon(
                _isEditing ? Icons.save : Icons.edit,
                color: kOrange),
            onPressed: () {
              setState(() {
                if (_isEditing) {
                  widget.itinerary.title =
                      _titleController.text;
                }
                _isEditing = !_isEditing;
              });
            },
          )
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // AI editing preview banner (shown when proposal is available)
          if (_isEditingWithAI && _proposedItinerary != null)
            Container(
              padding: const EdgeInsets.all(16),
              margin: const EdgeInsets.only(bottom: 20),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [kOrange.withValues(alpha: 0.15), kOrange.withValues(alpha: 0.08)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: kOrange.withValues(alpha: 0.4)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.auto_awesome, color: kOrange, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        'AI Proposed Changes',
                        style: GoogleFonts.inter(
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                          color: kDark,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Review the proposed itinerary below. Accept to apply changes or reject to keep the original.',
                    style: GoogleFonts.inter(fontSize: 12, color: kGray),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.check, size: 18),
                          label: const Text('Accept Changes'),
                          onPressed: _acceptChanges,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: kOrange,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton.icon(
                          icon: const Icon(Icons.close, size: 18),
                          label: const Text('Reject'),
                          onPressed: _rejectChanges,
                          style: OutlinedButton.styleFrom(
                            foregroundColor: kGray,
                            side: BorderSide(color: kBorder),
                            padding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          // Loading indicator while fetching proposal
          if (_isFetchingProposal)
            Container(
              padding: const EdgeInsets.all(20),
              margin: const EdgeInsets.only(bottom: 20),
              decoration: BoxDecoration(
                color: kOrange.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: kOrange.withValues(alpha: 0.2)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      color: kOrange,
                      strokeWidth: 2,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    'Generating AI proposal...',
                    style: GoogleFonts.inter(fontSize: 14, color: kGray),
                  ),
                ],
              ),
            ),
          Container(
            height: 260,
            margin: const EdgeInsets.only(bottom: 20),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: _isEditingWithAI ? kOrange : kBorder, width: _isEditingWithAI ? 2 : 1),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(19),
              child: Stack(
                children: [
                  FlutterMap(
                    options: MapOptions(
                      initialCenter: LatLng(
                          (_proposedItinerary ?? widget.itinerary).orderedWaypoints
                              .first.safeLatitude,
                          (_proposedItinerary ?? widget.itinerary).orderedWaypoints
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
                      if ((_proposedItinerary ?? widget.itinerary).routePoints
                          .isNotEmpty)
                        PolylineLayer(
                          polylines: <Polyline<
                              Object>>[
                            Polyline(
                              points: (_proposedItinerary ?? widget.itinerary)
                                  .routePoints,
                              color: _isEditingWithAI ? Colors.blue : kOrange,
                              strokeWidth: 5,
                            ),
                          ],
                        ),
                      MarkerLayer(markers: [
                        ...(_proposedItinerary ?? widget.itinerary).orderedWaypoints
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
                                            : (_isEditingWithAI ? Colors.blue : kOrange)),
                                    shape: BoxShape
                                        .circle,
                                    border: Border.all(
                                        color: selected
                                            ? (_isEditingWithAI ? Colors.blue : kOrange)
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
                                        ? (_isEditingWithAI ? Colors.blue : kOrange)
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
          Container(
            padding: const EdgeInsets.symmetric(
                horizontal: 16, vertical: 12),
            margin:
                const EdgeInsets.only(bottom: 20),
            decoration: BoxDecoration(
              color: _isEditingWithAI
                  ? Colors.blue.withValues(alpha: 0.08)
                  : kOrange.withValues(alpha: 0.08),
              borderRadius:
                  BorderRadius.circular(14),
              border: Border.all(
                  color: _isEditingWithAI
                      ? Colors.blue.withValues(alpha: 0.2)
                      : kOrange.withValues(alpha: 0.2)),
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
                      '${(_proposedItinerary ?? widget.itinerary).distanceKm.toStringAsFixed(1)} km',
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
                      '${((_proposedItinerary ?? widget.itinerary).durationMinutes / 60).toStringAsFixed(1)} hrs',
                      style: GoogleFonts.inter(
                          fontSize: 16,
                          fontWeight:
                              FontWeight.bold,
                          color: kDark)),
                ]),
              ],
            ),
          ),
          ...(_proposedItinerary ?? widget.itinerary).itinerary.entries.map(
              (entry) => DaySection(
                  day: entry.key,
                  stops: entry.value)),
        ],
      ),
    );
  }
}