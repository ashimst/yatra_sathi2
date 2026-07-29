import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/services/user_session.dart';
import 'package:mobile/screens/map_screen.dart';
import 'package:mobile/screens/place_detail_screen.dart';
import 'package:mobile/widgets/explore_card.dart';
import 'package:mobile/widgets/ai_chat_widget.dart';

class ExploreScreen extends StatefulWidget {
  final List<Place> places;
  const ExploreScreen({super.key, required this.places});

  @override
  State<ExploreScreen> createState() => _ExploreScreenState();
}

class _ExploreScreenState extends State<ExploreScreen> {
  String _selectedCategory = 'All';
  String _searchQuery = '';
  bool _showMap = false;

  List<String> get _categories {
    final cats = <String>{'All'};
    for (final p in widget.places) {
      if (p.category.isNotEmpty) cats.add(p.category);
    }
    return cats.toList();
  }

  List<Place> get _filtered {
    return widget.places.where((p) {
      if (_searchQuery.isNotEmpty &&
          !p.name
              .toLowerCase()
              .contains(_searchQuery.toLowerCase()) &&
          !p.safeDistrict
              .toLowerCase()
              .contains(_searchQuery.toLowerCase()) &&
          !p.safeDescription
              .toLowerCase()
              .contains(_searchQuery.toLowerCase())) {
        return false;
      }
      if (_selectedCategory != 'All' &&
          p.category != _selectedCategory) {
        return false;
      }
      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    if (_showMap) return _buildMapView();

    return Scaffold(
      backgroundColor: kCream,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding:
                  const EdgeInsets.fromLTRB(20, 20, 20, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Discover Nepal',
                      style: Theme.of(context)
                          .textTheme
                          .displayMedium),
                  const SizedBox(height: 14),
                  TextField(
                    decoration: InputDecoration(
                      hintText:
                          'Lakes, temples, mountain roads...',
                      hintStyle: GoogleFonts.inter(
                          color: kGray),
                      prefixIcon: const Icon(Icons.search,
                          color: kGray, size: 20),
                    ),
                    onChanged: (v) =>
                        setState(() => _searchQuery = v),
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    height: 38,
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      itemCount: _categories.length,
                      separatorBuilder: (_, _) =>
                          const SizedBox(width: 8),
                      itemBuilder: (context, i) {
                        final cat = _categories[i];
                        final active =
                            cat == _selectedCategory;
                        return GestureDetector(
                          onTap: () => setState(
                              () => _selectedCategory = cat),
                          child: AnimatedContainer(
                            duration: const Duration(
                                milliseconds: 200),
                            padding:
                                const EdgeInsets.symmetric(
                                    horizontal: 16,
                                    vertical: 9),
                            decoration: BoxDecoration(
                              color: active
                                  ? kDark
                                  : Colors.white,
                              borderRadius:
                                  BorderRadius.circular(
                                      20),
                              border: Border.all(
                                  color: active
                                      ? kDark
                                      : kBorder),
                            ),
                            child: Text(
                              cat,
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: active
                                    ? Colors.white
                                    : kDark,
                              ),
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: _filtered.isEmpty
                  ? const Center(
                      child: Text('No places found'))
                  : GridView.builder(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 4),
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        crossAxisSpacing: 12,
                        mainAxisSpacing: 12,
                        childAspectRatio: 0.75,
                      ),
                      itemCount: _filtered.length,
                      itemBuilder: (context, i) {
                        final place = _filtered[i];
                        return ExploreCard(
                          place: place,
                          isSaved: UserSession
                              .savedPlaceIds
                              .contains(place.id),
                          onSave: () => setState(() {
                            if (UserSession.savedPlaceIds
                                .contains(place.id)) {
                              UserSession.savedPlaceIds
                                  .remove(place.id);
                            } else {
                              UserSession.savedPlaceIds
                                  .add(place.id);
                            }
                            UserSession.persist();
                          }),
                          onTap: () => Navigator.push(
                              context,
                              MaterialPageRoute(
                                  builder: (_) =>
                                      PlaceDetailScreen(
                                          place: place))),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          FloatingActionButton(
            heroTag: 'ai_chat',
            onPressed: () {
              showModalBottomSheet(
                context: context,
                isScrollControlled: true,
                backgroundColor: Colors.transparent,
                builder: (context) => AIChatWidget(
                  screenContext: 'explore',
                  screenData: {
                    'category': _selectedCategory,
                    'search_query': _searchQuery,
                  },
                ),
              );
            },
            backgroundColor: kOrange,
            child: const Icon(Icons.smart_toy, color: Colors.white),
          ),
          const SizedBox(height: 12),
          FloatingActionButton.extended(
            heroTag: 'map',
            onPressed: () => setState(() => _showMap = true),
            backgroundColor: kDark,
            icon: const Icon(Icons.map_outlined, color: Colors.white),
            label: Text('See map',
                style: GoogleFonts.inter(
                    color: Colors.white, fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }

  Widget _buildMapView() {
    return MapScreen(
      places: widget.places,
      onBack: () => setState(() => _showMap = false),
    );
  }
}