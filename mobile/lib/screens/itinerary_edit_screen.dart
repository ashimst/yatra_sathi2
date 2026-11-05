import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';
import 'package:http/http.dart' as http;
import 'package:mobile/constants.dart';
import 'package:mobile/models/created_itinerary.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/screens/place_detail_screen.dart';
import 'package:mobile/widgets/day_section.dart';
import 'package:mobile/widgets/ai_chat_widget.dart';

class ItineraryEditScreen extends StatefulWidget {
  final CreatedItinerary itinerary;
  const ItineraryEditScreen({super.key, required this.itinerary});

  @override
  State<ItineraryEditScreen> createState() => _ItineraryEditScreenState();
}

class _ItineraryEditScreenState extends State<ItineraryEditScreen> {
  late CreatedItinerary _itinerary;
  Place? _selectedItineraryPlace;
  String? _workspaceId;
  bool _isLoading = false;
  List<Map<String, dynamic>> _versionHistory = [];
  int _currentVersionIndex = 0;
  
  // Proposal workflow state
  Map<String, dynamic>? _currentProposal;
  bool _isProposalMode = false;
  bool _isProposalLoading = false;

  @override
  void initState() {
    super.initState();
    _itinerary = widget.itinerary;
    _initializeWorkspace();
  }

  Future<void> _initializeWorkspace() async {
    setState(() => _isLoading = true);
    
    try {
      // Create or load workspace
      final response = await http.post(
        Uri.parse('$kBaseUrl/workspace'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'user_id': 'default_user',
          'name': _itinerary.title,
          'origin_lat': _itinerary.orderedWaypoints.first.latitude,
          'origin_lng': _itinerary.orderedWaypoints.first.longitude,
          'destination_lat': _itinerary.orderedWaypoints.last.latitude,
          'destination_lng': _itinerary.orderedWaypoints.last.longitude,
          'start_date': DateTime.now().toIso8601String(),
          'end_date': DateTime.now().add(Duration(days: _itinerary.days)).toIso8601String(),
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _workspaceId = data['workspace_id'];
        await _loadVersionHistory();
      }
    } catch (e) {
      debugPrint('Error initializing workspace: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadVersionHistory() async {
    if (_workspaceId == null) return;
    
    try {
      final response = await http.get(
        Uri.parse('$kBaseUrl/workspace/$_workspaceId/versions'),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _versionHistory = List<Map<String, dynamic>>.from(data['versions']);
          _currentVersionIndex = _versionHistory.length - 1;
        });
      }
    } catch (e) {
      debugPrint('Error loading version history: $e');
    }
  }

  void _openAIChat() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => AIChatWidget(
        screenContext: 'itinerary_edit',
        screenData: {
          'origin': _itinerary.from,
          'destination': _itinerary.to,
          'duration_days': _itinerary.days,
          'interests': [],
          'budget_level': _itinerary.budget,
          'pace': _itinerary.pace,
          'workspace_id': _workspaceId,
        },
        itineraryContext: {
          'id': _itinerary.id,
          'title': _itinerary.title,
          'from': _itinerary.from,
          'to': _itinerary.to,
          'days': _itinerary.days,
          'itinerary': _itinerary.itinerary,
          'workspace_id': _workspaceId,
        },
        onNavigate: () {
          // Handle navigation if needed
        },
        onEditApplied: (edits) {
          _applyProposalEdit(edits);
        },
      ),
    );
  }

  Future<void> _applyEdit(Map<String, dynamic> edits) async {
    if (_workspaceId == null) return;
    
    setState(() => _isLoading = true);
    
    try {
      // Execute operation via workspace API
      final response = await http.post(
        Uri.parse('$kBaseUrl/workspace/$_workspaceId/execute'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'operation_type': edits['type'],
          'args': edits,
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        // Update local itinerary from workspace
        await _refreshFromWorkspace();
        
        // Reload version history
        await _loadVersionHistory();
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(data['result']['explanation'] ?? 'Changes applied')),
        );
      }
    } catch (e) {
      debugPrint('Error applying edit: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to apply changes')),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _applyProposalEdit(Map<String, dynamic> edits) async {
    if (_workspaceId == null) return;
    
    setState(() => _isProposalLoading = true);
    
    try {
      List<Map<String, dynamic>> operations = [];
      if (edits['edits'] is List && (edits['edits'] as List).isNotEmpty) {
        for (var e in (edits['edits'] as List)) {
          if (e is Map<String, dynamic>) {
            operations.add({
              'type': e['type'] ?? 'modify_itinerary',
              'args': e,
            });
          }
        }
      }
      if (operations.isEmpty) {
        operations = [
          {
            'type': edits['type'] ?? 'modify_itinerary',
            'args': edits,
          }
        ];
      }

      // Create proposal using proposal API
      final response = await http.post(
        Uri.parse('$kBaseUrl/workspace/$_workspaceId/propose'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'operations': operations,
          'user_id': 'default_user',
          'screen_context': 'itinerary_edit',
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        if (data['success']) {
          // Show proposal preview
          setState(() {
            _currentProposal = data;
            _isProposalMode = true;
          });
          
          _showProposalDialog(data);
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(data['error'] ?? 'Failed to create proposal')),
          );
        }
      }
    } catch (e) {
      debugPrint('Error creating proposal: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to create proposal')),
      );
    } finally {
      setState(() => _isProposalLoading = false);
    }
  }

  void _showProposalDialog(Map<String, dynamic> proposalData) {
    final changes = proposalData['changes'] as List;
    final warnings = proposalData['warnings'] as List;
    final explanation = proposalData['explanation'] as String;
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Review Proposed Changes'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(explanation, style: GoogleFonts.inter(fontSize: 14)),
              const SizedBox(height: 16),
              const Text('Changes:', style: TextStyle(fontWeight: FontWeight.bold)),
              ...changes.map((change) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Text('• ${change['explanation']}', style: GoogleFonts.inter(fontSize: 12)),
              )),
              if (warnings.isNotEmpty) ...[
                const SizedBox(height: 12),
                const Text('Warnings:', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.orange)),
                ...warnings.map((warning) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Text('⚠ $warning', style: GoogleFonts.inter(fontSize: 12, color: Colors.orange)),
                )),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              setState(() {
                _currentProposal = null;
                _isProposalMode = false;
              });
              Navigator.pop(context);
            },
            child: const Text('Reject'),
          ),
          ElevatedButton(
            onPressed: () {
              _acceptProposal(proposalData['proposal_id']);
              Navigator.pop(context);
            },
            style: ElevatedButton.styleFrom(backgroundColor: kOrange),
            child: const Text('Accept', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  Future<void> _acceptProposal(String proposalId) async {
    if (_workspaceId == null || proposalId == null) return;
    
    setState(() => _isProposalLoading = true);
    
    try {
      final response = await http.post(
        Uri.parse('$kBaseUrl/workspace/$_workspaceId/proposals/$proposalId/action'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'action': 'accept',
          'create_version': true,
          'version_description': 'Accepted AI proposal',
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        if (data['success']) {
          // Update local itinerary from workspace
          await _refreshFromWorkspace();
          
          // Reload version history
          await _loadVersionHistory();
          
          setState(() {
            _currentProposal = null;
            _isProposalMode = false;
          });
          
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Changes accepted and applied')),
          );
        }
      }
    } catch (e) {
      debugPrint('Error accepting proposal: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to accept changes')),
      );
    } finally {
      setState(() => _isProposalLoading = false);
    }
  }

  Future<void> _refreshFromWorkspace() async {
    if (_workspaceId == null) return;
    
    try {
      final response = await http.get(
        Uri.parse('$kBaseUrl/workspace/$_workspaceId'),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        // Update itinerary from workspace data
        // This would need to be adapted based on the actual workspace structure
        debugPrint('Workspace refreshed: ${data['workspace']['id']}');
      }
    } catch (e) {
      debugPrint('Error refreshing from workspace: $e');
    }
  }

  Future<void> _undo() async {
    if (_workspaceId == null) return;
    
    setState(() => _isLoading = true);
    
    try {
      final response = await http.post(
        Uri.parse('$kBaseUrl/workspace/$_workspaceId/undo'),
      );
      
      if (response.statusCode == 200) {
        await _refreshFromWorkspace();
        await _loadVersionHistory();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Undo successful')),
        );
      }
    } catch (e) {
      debugPrint('Error undoing: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _redo() async {
    if (_workspaceId == null) return;
    
    setState(() => _isLoading = true);
    
    try {
      final response = await http.post(
        Uri.parse('$kBaseUrl/workspace/$_workspaceId/redo'),
      );
      
      if (response.statusCode == 200) {
        await _refreshFromWorkspace();
        await _loadVersionHistory();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Redo successful')),
        );
      }
    } catch (e) {
      debugPrint('Error redoing: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kCream,
      appBar: AppBar(
        backgroundColor: kCream,
        elevation: 0,
        title: Text(
          'Edit Itinerary',
          style: GoogleFonts.inter(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: kDark,
          ),
        ),
        actions: [
          if (_currentVersionIndex > 0)
            IconButton(
              icon: const Icon(Icons.undo, color: kDark),
              onPressed: _undo,
              tooltip: 'Undo',
            ),
          if (_currentVersionIndex < _versionHistory.length - 1)
            IconButton(
              icon: const Icon(Icons.redo, color: kDark),
              onPressed: _redo,
              tooltip: 'Redo',
            ),
          IconButton(
            icon: const Icon(Icons.smart_toy, color: kOrange),
            onPressed: _openAIChat,
            tooltip: 'AI Assistant',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: kOrange))
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
          // Map section
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
                          _itinerary.orderedWaypoints.first.safeLatitude,
                          _itinerary.orderedWaypoints.first.safeLongitude),
                      initialZoom: 7.5,
                      onTap: (_, _) => setState(() => _selectedItineraryPlace = null),
                    ),
                    children: [
                      TileLayer(
                        urlTemplate:
                            'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        userAgentPackageName: 'com.yatrasathi.app',
                      ),
                      if (_itinerary.routePoints.isNotEmpty)
                        PolylineLayer(
                          polylines: [
                            Polyline(
                              points: _itinerary.routePoints,
                              color: kOrange,
                              strokeWidth: 5,
                            ),
                          ],
                        ),
                      MarkerLayer(markers: [
                        ..._itinerary.orderedWaypoints.map((wp) {
                          final isStartEnd = wp.id == 'start' || wp.id == 'end';
                          final selected = _selectedItineraryPlace?.id == wp.id;
                          return Marker(
                            point: LatLng(wp.safeLatitude, wp.safeLongitude),
                            width: selected ? 48 : (isStartEnd ? 42 : 32),
                            height: selected ? 48 : (isStartEnd ? 42 : 32),
                            child: GestureDetector(
                              onTap: () => setState(() => _selectedItineraryPlace = wp),
                              child: Tooltip(
                                message: '${wp.name}\n${wp.category}',
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: selected
                                        ? Colors.white
                                        : (isStartEnd ? kDark : kOrange),
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                        color: selected ? kOrange : Colors.white,
                                        width: 2),
                                    boxShadow: const [
                                      BoxShadow(
                                          color: Colors.black26,
                                          blurRadius: 4,
                                          offset: Offset(0, 2))
                                    ],
                                  ),
                                  child: Icon(
                                    wp.id == 'start'
                                        ? Icons.play_arrow
                                        : wp.id == 'end'
                                            ? Icons.flag
                                            : Icons.location_on,
                                    size: isStartEnd ? 18 : 14,
                                    color: selected ? kOrange : Colors.white,
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
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Expanded(
                                    child: Text(
                                      _selectedItineraryPlace!.name,
                                      style: GoogleFonts.inter(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 14,
                                          color: kDark),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  GestureDetector(
                                    onTap: () =>
                                        setState(() => _selectedItineraryPlace = null),
                                    child: const Icon(Icons.close,
                                        size: 18, color: kGray),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 2),
                              Text(
                                _selectedItineraryPlace!.category,
                                style: GoogleFonts.inter(
                                    color: kOrange,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600),
                              ),
                              if (_selectedItineraryPlace!.safeDescription.isNotEmpty) ...[
                                const SizedBox(height: 6),
                                Text(
                                  _selectedItineraryPlace!.safeDescription,
                                  style: GoogleFonts.inter(
                                      color: kGray, fontSize: 11),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                              if (_selectedItineraryPlace!.id != 'start' &&
                                  _selectedItineraryPlace!.id != 'end') ...[
                                const SizedBox(height: 6),
                                Align(
                                  alignment: Alignment.centerRight,
                                  child: TextButton(
                                    style: TextButton.styleFrom(
                                      padding: EdgeInsets.zero,
                                      minimumSize: Size.zero,
                                      tapTargetSize:
                                          MaterialTapTargetSize.shrinkWrap,
                                    ),
                                    onPressed: () {
                                      Navigator.push(
                                          context,
                                          MaterialPageRoute(
                                              builder: (_) => PlaceDetailScreen(
                                                  place: _selectedItineraryPlace!)));
                                    },
                                    child: Text('View Details',
                                        style: GoogleFonts.inter(
                                            fontWeight: FontWeight.bold,
                                            color: kOrange,
                                            fontSize: 12)),
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
          // Summary card
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            margin: const EdgeInsets.only(bottom: 20),
            decoration: BoxDecoration(
              color: kOrange.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: kOrange.withValues(alpha: 0.2)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                Column(children: [
                  Text('TOTAL DISTANCE',
                      style: GoogleFonts.inter(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: kGray)),
                  const SizedBox(height: 4),
                  Text('${_itinerary.distanceKm.toStringAsFixed(1)} km',
                      style: GoogleFonts.inter(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: kDark)),
                ]),
                Column(children: [
                  Text('DRIVE TIME',
                      style: GoogleFonts.inter(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: kGray)),
                  const SizedBox(height: 4),
                  Text('${(_itinerary.durationMinutes / 60).toStringAsFixed(1)} hrs',
                      style: GoogleFonts.inter(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: kDark)),
                ]),
              ],
            ),
          ),
          // AI suggestion banner
          Container(
            padding: const EdgeInsets.all(16),
            margin: const EdgeInsets.only(bottom: 20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [kOrange.withValues(alpha: 0.1), kOrange.withValues(alpha: 0.05)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: kOrange.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.auto_awesome, color: kOrange, size: 24),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('AI-Powered Editing',
                          style: GoogleFonts.inter(
                              fontWeight: FontWeight.bold,
                              fontSize: 14,
                              color: kDark)),
                      const SizedBox(height: 2),
                      Text('Tap the AI icon to get smart suggestions for your itinerary',
                          style: GoogleFonts.inter(fontSize: 12, color: kGray)),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.arrow_forward, color: kOrange),
                  onPressed: _openAIChat,
                ),
              ],
            ),
          ),
          // Day sections
          ..._itinerary.itinerary.entries.map((entry) => DaySection(
              day: entry.key, stops: entry.value)),
        ],
      ),
    );
  }
}
