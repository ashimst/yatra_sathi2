import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/services/user_session.dart';
import 'package:mobile/widgets/placeholder_image.dart';
import 'package:mobile/screens/place_detail_screen.dart';
import 'package:mobile/screens/saved_itinerary_detail_screen.dart';
import 'package:mobile/widgets/ai_chat_widget.dart';

class SavedScreen extends StatefulWidget {
  final List<Place> places;
  const SavedScreen({super.key, required this.places});

  @override
  State<SavedScreen> createState() => _SavedScreenState();
}

class _SavedScreenState extends State<SavedScreen> {
  @override
  Widget build(BuildContext context) {
    final savedPlaces = widget.places
        .where(
            (p) => UserSession.savedPlaceIds.contains(p.id))
        .toList();
    final savedIts = UserSession.savedItineraries;

    return Scaffold(
      backgroundColor: kCream,
      body: DefaultTabController(
        length: 2,
        child: Column(
          children: [
            Padding(
              padding: EdgeInsets.fromLTRB(
                  20,
                  MediaQuery.of(context).padding.top +
                      20,
                  20,
                  0),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text('Saved',
                    style: Theme.of(context)
                        .textTheme
                        .displayMedium),
              ),
            ),
            const TabBar(
              indicatorColor: kOrange,
              labelColor: kOrange,
              unselectedLabelColor: kGray,
              tabs: [
                Tab(text: 'Places'),
                Tab(text: 'Roadtrips'),
              ],
            ),
            Expanded(
              child: TabBarView(
                children: [
                  // Places View
                  savedPlaces.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize:
                                MainAxisSize.min,
                            children: [
                              const Icon(
                                  Icons
                                      .location_on_outlined,
                                  size: 64,
                                  color: kBorder),
                              const SizedBox(
                                  height: 12),
                              Text(
                                  'No saved places yet',
                                  style: GoogleFonts.inter(
                                      fontSize: 16,
                                      color:
                                          kGray)),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding:
                              const EdgeInsets.all(
                                  20),
                          itemCount:
                              savedPlaces.length,
                          itemBuilder: (ctx, i) =>
                              Container(
                            margin: const EdgeInsets
                                .only(bottom: 10),
                            decoration: BoxDecoration(
                                color: kCardBg,
                                borderRadius:
                                    BorderRadius
                                        .circular(14),
                                border: Border.all(
                                    color: kBorder)),
                            child: ClipRRect(
                              borderRadius:
                                  BorderRadius
                                      .circular(14),
                              child: ListTile(
                                contentPadding:
                                    const EdgeInsets
                                        .all(10),
                                tileColor: kCardBg,
                                leading: ClipRRect(
                                  borderRadius:
                                      BorderRadius
                                          .circular(
                                              10),
                                  child: savedPlaces[i]
                                          .imageUrl
                                          .isNotEmpty
                                      ? Image.network(
                                          savedPlaces[i]
                                              .imageUrl,
                                          width: 60,
                                          height: 60,
                                          fit: BoxFit
                                              .cover,
                                          errorBuilder: (c,
                                                  e,
                                                  s) =>
                                              buildPlaceholderImage(
                                                  savedPlaces[i]
                                                      .category))
                                      : buildPlaceholderImage(
                                          savedPlaces[i]
                                              .category),
                                ),
                                title: Text(
                                    savedPlaces[i]
                                        .name,
                                    style: GoogleFonts.inter(
                                        fontWeight:
                                            FontWeight
                                                .w600,
                                        color:
                                            kDark)),
                                subtitle: Text(
                                    savedPlaces[i]
                                        .safeDistrict,
                                    style: GoogleFonts.inter(
                                        fontSize: 12,
                                        color:
                                            kGray)),
                                trailing:
                                    IconButton(
                                  icon: const Icon(
                                      Icons.favorite,
                                      color: kOrange,
                                      size: 20),
                                  onPressed: () {
                                    setState(() {
                                      UserSession
                                          .savedPlaceIds
                                          .remove(savedPlaces[
                                                  i]
                                              .id);
                                    });
                                  },
                                ),
                                onTap: () {
                                  Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                          builder: (_) =>
                                              PlaceDetailScreen(
                                                  place:
                                                      savedPlaces[
                                                          i])));
                                },
                              ),
                            ),
                          ),
                        ),
                  // Roadtrips View
                  savedIts.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize:
                                MainAxisSize.min,
                            children: [
                              const Icon(
                                  Icons.map_outlined,
                                  size: 64,
                                  color: kBorder),
                              const SizedBox(
                                  height: 12),
                              Text(
                                  'No saved roadtrips yet',
                                  style: GoogleFonts.inter(
                                      fontSize: 16,
                                      color:
                                          kGray)),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding:
                              const EdgeInsets.all(
                                  20),
                          itemCount:
                              savedIts.length,
                          itemBuilder: (ctx, i) {
                            final it = savedIts[i];
                            return Container(
                              margin: const EdgeInsets
                                  .only(bottom: 10),
                              decoration: BoxDecoration(
                                  color: kCardBg,
                                  borderRadius:
                                      BorderRadius
                                          .circular(14),
                                  border: Border.all(
                                      color:
                                          kBorder)),
                              child: ClipRRect(
                                borderRadius:
                                    BorderRadius
                                        .circular(14),
                                child: ListTile(
                                  contentPadding:
                                      const EdgeInsets
                                          .all(12),
                                  tileColor:
                                      kCardBg,
                                  title: Text(
                                      it.title,
                                      style: GoogleFonts.inter(
                                          fontWeight:
                                              FontWeight
                                                  .bold,
                                          color:
                                              kDark)),
                                  subtitle: Text(
                                      '${it.from} → ${it.to} · ${it.days} Days',
                                      style: GoogleFonts.inter(
                                          fontSize:
                                              12,
                                          color:
                                              kGray)),
                                  trailing:
                                      IconButton(
                                    icon: const Icon(
                                        Icons.delete_outline,
                                        color: Colors
                                            .redAccent),
                                    onPressed: () {
                                      setState(() {
                                        UserSession
                                            .savedItineraries
                                            .removeAt(
                                                i);
                                      });
                                    },
                                  ),
                                  onTap: () {
                                    Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                            builder: (_) =>
                                                SavedItineraryDetailScreen(
                                                    itinerary:
                                                        it)));
                                  },
                                ),
                              ),
                            );
                          },
                        ),
                ],
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          showModalBottomSheet(
            context: context,
            isScrollControlled: true,
            backgroundColor: Colors.transparent,
            builder: (context) => AIChatWidget(
              screenContext: 'saved',
              screenData: {
                'saved_places_count': widget.places
                    .where((p) => UserSession.savedPlaceIds.contains(p.id))
                    .length,
                'saved_itineraries_count': UserSession.savedItineraries.length,
              },
            ),
          );
        },
        backgroundColor: kOrange,
        child: const Icon(Icons.smart_toy, color: Colors.white),
      ),
    );
  }
}