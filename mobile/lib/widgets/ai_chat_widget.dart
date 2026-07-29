import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/models/created_itinerary.dart';
import 'package:mobile/services/ai_service.dart';
import 'package:mobile/services/user_session.dart';
import 'package:mobile/services/user_storage.dart';

class AIChatWidget extends StatefulWidget {
  final String screenContext;
  final Map<String, dynamic>? screenData;
  final Map<String, dynamic>? itineraryContext;
  final VoidCallback? onNavigate;
  final Function(Map<String, dynamic>)? onEditApplied;

  const AIChatWidget({
    super.key,
    required this.screenContext,
    this.screenData,
    this.itineraryContext,
    this.onNavigate,
    this.onEditApplied,
  });

  @override
  State<AIChatWidget> createState() => _AIChatWidgetState();
}

class _AIChatWidgetState extends State<AIChatWidget> {
  final List<Map<String, dynamic>> _chatMessages = [
    {
      'role': 'assistant',
      'content':
          'Namaste! I am YatraSathi, your AI travel assistant. How can I help you today?'
    }
  ];
  bool _isChatLoading = false;
  final TextEditingController _chatController = TextEditingController();
  final ScrollController _chatScrollController = ScrollController();

  String? _cachedSessionId;

  String _resolveSessionId() {
    if (_cachedSessionId != null) return _cachedSessionId!;
    // Each widget instance gets a stable, unique session id that persists
    // for the lifetime of the widget.  If a real user id is available it's
    // appended to make cross-user collisions impossible.
    final String userId = UserSession.loggedInUser ?? "guest";
    _cachedSessionId = AIService.generateSessionId() + '_' + userId;
    return _cachedSessionId!;
  }

  @override
  void dispose() {
    _chatController.dispose();
    _chatScrollController.dispose();
    super.dispose();
  }

  dynamic _makeJsonSerializable(dynamic value) {
    if (value == null) {
      return null;
    }
    
    if (value is String || value is num || value is bool) {
      return value;
    }
    
    if (value is List) {
      return value.map((item) => _makeJsonSerializable(item)).toList();
    }
    
    if (value is Map) {
      final Map<String, dynamic> result = {};
      value.forEach((key, val) {
        result[key.toString()] = _makeJsonSerializable(val);
      });
      return result;
    }
    
    // Handle custom objects by converting to Map if possible
    try {
      // Try to convert to JSON using toJson method if available
      if (value is Place) {
        return {
          'id': value.id,
          'name': value.name,
          'latitude': value.latitude,
          'longitude': value.longitude,
          'category': value.category,
          'description': value.description,
          'images': value.images,
        };
      }
      
      // Fallback: try to convert to string representation
      return value.toString();
    } catch (e) {
      return value.toString();
    }
  }

  Future<void> _sendChatMessage() async {
    final text = _chatController.text.trim();
    if (text.isEmpty) return;

    _chatController.clear();
    setState(() {
      _chatMessages.add({'role': 'user', 'content': text});
      _isChatLoading = true;
    });

    Future.delayed(const Duration(milliseconds: 100), () {
      if (_chatScrollController.hasClients) {
        _chatScrollController.animateTo(
          _chatScrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });

    try {
      final sessionId = _resolveSessionId();
      final userId = UserSession.loggedInUser;

      Map<String, dynamic>? serializableItineraryContext;
      if (widget.itineraryContext != null) {
        serializableItineraryContext = _makeJsonSerializable(widget.itineraryContext!);
      } else if (UserSession.savedItineraries.isNotEmpty) {
        final firstSaved = UserSession.savedItineraries.first;
        serializableItineraryContext = {
          'id': firstSaved.id,
          'title': firstSaved.title,
          'origin': firstSaved.from,
          'destination': firstSaved.to,
          'days': firstSaved.days,
          'itinerary': firstSaved.itinerary,
        };
      }

      final List<Map<String, dynamic>> createdItinerariesPayload = [];
      for (final it in UserSession.savedItineraries) {
        final Map<String, List<String>> cleanItinerary = {};
        it.itinerary.forEach((dayKey, stops) {
          cleanItinerary[dayKey] = stops.map((stop) {
            final time = stop['time'] as String? ?? '';
            final name = stop['name'] as String? ?? '';
            return time.isNotEmpty ? '$time: $name' : name;
          }).toList();
        });

        createdItinerariesPayload.add({
          'id': it.id,
          'title': it.title,
          'origin': it.from,
          'destination': it.to,
          'days': it.days,
          'budget': it.budget,
          'pace': it.pace,
          'travelers': it.travelers,
          'itinerary_data': cleanItinerary,
        });
      }

      debugPrint('AIChatWidget → AIService.chat(session=$sessionId, user=$userId)');

      final Map<String, dynamic> data = await AIService.chat(
        sessionId: sessionId,
        userId: userId,
        message: text,
        screenContext: widget.screenContext,
        screenData: widget.screenData,
        itineraryContext: serializableItineraryContext,
        createdItineraries: createdItinerariesPayload,
      );

      debugPrint('AIChatWidget ← response: session_id=${data['session_id']}');
      final responseText = data['response_text'] ?? '';
      final proposedAction = data['proposed_action'] as Map<String, dynamic>?;
      final redirectScreen = data['redirect_screen'] as String?;

      setState(() {
        _chatMessages.add({
          'role': 'assistant',
          'content': responseText,
          'proposed_action': proposedAction,
          'redirect_screen': redirectScreen,
        });
      });

      if (redirectScreen != null && widget.onNavigate != null) {
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) widget.onNavigate!();
        });
      }
    } on Exception catch (e) {
      debugPrint('AIChatWidget error: $e');
      setState(() {
        _chatMessages.add({
          'role': 'assistant',
          'content':
              'Network/AI service error: $e. Make sure the backend is running and AI_ENABLED=true in its .env file.',
        });
      });
    } finally {
      setState(() {
        _isChatLoading = false;
      });

      Future.delayed(const Duration(milliseconds: 100), () {
        if (_chatScrollController.hasClients) {
          _chatScrollController.animateTo(
            _chatScrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
      });
    }
  }

  void _executeProposedAction(Map<String, dynamic> action) {
    final type = action['type'];
    final args = action['args'] as Map<String, dynamic>? ?? {};

    if (type == 'apply_edit') {
      final updatedItData = args['updated_itinerary'] as Map<String, dynamic>?;
      if (updatedItData != null && updatedItData['id'] != null) {
        final String itId = updatedItData['id'].toString();
        final int idx = UserSession.savedItineraries.indexWhere((it) => it.id == itId);
        if (idx != -1) {
          final existing = UserSession.savedItineraries[idx];
          
          Map<String, List<Map<String, dynamic>>> parsedSchedule = {};
          if (updatedItData['itinerary'] is Map) {
            (updatedItData['itinerary'] as Map).forEach((k, v) {
              if (v is List) {
                parsedSchedule[k.toString()] = v.map((item) {
                  if (item is Map) {
                    return Map<String, dynamic>.from(item);
                  } else {
                    return {'name': item.toString(), 'time': ''};
                  }
                }).toList();
              }
            });
          }

          final updatedIt = CreatedItinerary(
            id: existing.id,
            title: updatedItData['title']?.toString() ?? existing.title,
            from: updatedItData['origin']?.toString() ?? updatedItData['from']?.toString() ?? existing.from,
            to: updatedItData['destination']?.toString() ?? updatedItData['to']?.toString() ?? existing.to,
            days: (updatedItData['days'] as num?)?.toInt() ?? existing.days,
            travelers: (updatedItData['travelers'] as num?)?.toInt() ?? existing.travelers,
            budget: updatedItData['budget']?.toString() ?? existing.budget,
            pace: updatedItData['pace']?.toString() ?? existing.pace,
            diet: existing.diet,
            author: existing.author,
            likes: existing.likes,
            isPublic: existing.isPublic,
            itinerary: parsedSchedule.isNotEmpty ? parsedSchedule : existing.itinerary,
            orderedWaypoints: existing.orderedWaypoints,
            routePoints: existing.routePoints,
            distanceKm: (updatedItData['distance_km'] as num?)?.toDouble() ?? existing.distanceKm,
            durationMinutes: (updatedItData['duration_minutes'] as num?)?.toDouble() ?? existing.durationMinutes,
          );

          UserSession.savedItineraries[idx] = updatedIt;
          UserStorage.saveSavedItineraries(UserSession.savedItineraries);
        }
      }

      if (widget.onEditApplied != null) {
        widget.onEditApplied!(args);
      }

      setState(() {
        for (var msg in _chatMessages) {
          if (msg['proposed_action'] != null) {
            msg['proposed_action'] = null;
          }
        }
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Itinerary updated with new schedule & route!')),
      );
      return;
    }

    setState(() {
      for (var msg in _chatMessages) {
        if (msg['proposed_action'] != null) {
          msg['proposed_action'] = null;
        }
      }
    });

    if (type == 'generate_itinerary') {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Itinerary generation initiated')),
      );
    } else if (type == 'show_recommendations') {
      _showRecommendationsDialog(args);
    } else if (type == 'navigate_to' && widget.onNavigate != null) {
      widget.onNavigate!();
    } else {
      // Unknown / not-yet-implemented action types: do NOT silently tell the
      // user "approved" because that's misleading.  State explicitly that
      // it's not wired yet, and leave a console trace.
      debugPrint('AIChatWidget: unsupported proposed_action type=$type args=$args');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          behavior: SnackBarBehavior.floating,
          content: Text(
            "'$type' is not implemented yet in the frontend. "
            "The action was NOT applied.",
          ),
          duration: const Duration(seconds: 4),
          backgroundColor: Colors.deepOrange,
        ),
      );
    }
  }

  void _showRecommendationsDialog(Map<String, dynamic> args) {
    final recommendations = args['recommendations'] as List<dynamic>?;
    
    if (recommendations == null || recommendations.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No recommendations available')),
      );
      return;
    }

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Recommendations', style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: recommendations.length,
            itemBuilder: (context, index) {
              final rec = recommendations[index] as Map<String, dynamic>;
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  title: Text(rec['place_name'] ?? 'Unknown', style: GoogleFonts.inter(fontWeight: FontWeight.w600)),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(rec['justification'] ?? '', style: GoogleFonts.inter(fontSize: 12, color: kGray)),
                      if (rec['distance_km'] != null)
                        Text('${rec['distance_km'].toStringAsFixed(1)} km away', style: GoogleFonts.inter(fontSize: 11)),
                    ],
                  ),
                  trailing: IconButton(
                    icon: const Icon(Icons.add_circle, color: kOrange),
                    onPressed: () {
                      Navigator.pop(context);
                      // Apply the recommendation
                      widget.onEditApplied?.call({
                        'type': 'add_stop',
                        'place_id': rec['place_id'],
                        'day': args['day'] ?? 1,
                        'justification': rec['justification'],
                      });
                    },
                  ),
                ),
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Close', style: GoogleFonts.inter(color: kGray)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.70,
      decoration: const BoxDecoration(
        color: kCream,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        boxShadow: [
          BoxShadow(color: Colors.black26, blurRadius: 10, spreadRadius: 2)
        ],
      ),
      child: Column(
        children: [
          Container(
            margin: const EdgeInsets.symmetric(vertical: 12),
            height: 5,
            width: 40,
            decoration: BoxDecoration(
                color: kGray.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(10)),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                          color: kOrange.withValues(alpha: 0.1),
                          shape: BoxShape.circle),
                      child: const Icon(Icons.assistant, color: kOrange, size: 20),
                    ),
                    const SizedBox(width: 10),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('YatraSathi Assistant',
                            style: GoogleFonts.inter(
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                                color: kDark)),
                        Text('Powered by LangGraph AI',
                            style: GoogleFonts.inter(
                                fontSize: 11,
                                color: kGray,
                                fontWeight: FontWeight.w500)),
                      ],
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: kDark),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
          ),
          const Divider(color: kBorder),
          Expanded(
            child: ListView.builder(
              controller: _chatScrollController,
              padding: const EdgeInsets.all(16),
              itemCount: _chatMessages.length,
              itemBuilder: (context, index) {
                final msg = _chatMessages[index];
                final isUser = msg['role'] == 'user';
                final proposedAction =
                    msg['proposed_action'] as Map<String, dynamic>?;

                return Column(
                  crossAxisAlignment:
                      isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                  children: [
                    Container(
                      constraints: BoxConstraints(
                          maxWidth: MediaQuery.of(context).size.width * 0.75),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 12),
                      margin: const EdgeInsets.only(bottom: 8),
                      decoration: BoxDecoration(
                        color: isUser ? kOrange : Colors.white,
                        borderRadius: BorderRadius.only(
                          topLeft: const Radius.circular(16),
                          topRight: const Radius.circular(16),
                          bottomLeft: Radius.circular(isUser ? 16 : 4),
                          bottomRight: Radius.circular(isUser ? 4 : 16),
                        ),
                        border: isUser
                            ? null
                            : Border.all(color: kBorder),
                      ),
                      child: Text(
                        msg['content'] ?? '',
                        style: GoogleFonts.inter(
                          color: isUser ? Colors.white : kDark,
                          fontSize: 14,
                          height: 1.4,
                        ),
                      ),
                    ),
                    if (proposedAction != null) ...[
                      Container(
                        margin: const EdgeInsets.only(bottom: 12, left: 4),
                        child: Card(
                          color: Colors.white,
                          elevation: 2,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                            side: const BorderSide(color: kOrange, width: 1.5),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    const Icon(Icons.info_outline,
                                        color: kOrange, size: 18),
                                    const SizedBox(width: 8),
                                    Text(
                                      'Confirm Action',
                                      style: GoogleFonts.inter(
                                          fontWeight: FontWeight.bold,
                                          fontSize: 13,
                                          color: kDark),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  proposedAction['explanation'] ??
                                      'Apply changes to trip',
                                  style: GoogleFonts.inter(
                                      fontSize: 12, color: kGray),
                                ),
                                const SizedBox(height: 10),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.end,
                                  children: [
                                    TextButton(
                                      onPressed: () {
                                        setState(() {
                                          msg['proposed_action'] = null;
                                        });
                                      },
                                      child: Text('Ignore',
                                          style: GoogleFonts.inter(
                                              color: kGray, fontSize: 12)),
                                    ),
                                    const SizedBox(width: 8),
                                    ElevatedButton(
                                      style: ElevatedButton.styleFrom(
                                          backgroundColor: kOrange,
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 16, vertical: 8),
                                          minimumSize: Size.zero,
                                          shape: RoundedRectangleBorder(
                                              borderRadius:
                                                  BorderRadius.circular(8))),
                                      onPressed: () {
                                        _executeProposedAction(proposedAction);
                                      },
                                      child: Text('Approve',
                                          style: GoogleFonts.inter(
                                              color: Colors.white,
                                              fontSize: 12,
                                              fontWeight:
                                                  FontWeight.bold)),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ],
                );
              },
            ),
          ),
          if (_isChatLoading)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Center(
                child: SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(
                    color: kOrange,
                    strokeWidth: 2.5,
                  ),
                ),
              ),
            ),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: kBorder)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _chatController,
                    decoration: InputDecoration(
                      hintText: 'Ask assistant anything...',
                      hintStyle:
                          GoogleFonts.inter(color: kGray, fontSize: 14),
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
                      filled: false,
                      contentPadding: EdgeInsets.zero,
                    ),
                    style: GoogleFonts.inter(color: kDark, fontSize: 14),
                    onSubmitted: (_) => _sendChatMessage(),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send, color: kOrange),
                  onPressed: _sendChatMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
