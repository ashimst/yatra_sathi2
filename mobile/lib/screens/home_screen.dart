import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/services/user_session.dart';
import 'package:mobile/services/weather_service.dart';
import 'package:mobile/widgets/weather_card.dart';
import 'package:mobile/widgets/featured_trip_card.dart';
import 'package:mobile/widgets/trending_list_tile.dart';
import 'package:mobile/widgets/community_card.dart';

class HomeScreen extends StatefulWidget {
  final List<Place> places;
  final void Function(int) onSwitchTab;

  const HomeScreen({
    super.key,
    required this.places,
    required this.onSwitchTab,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  String _weatherCity = 'Kathmandu';
  int _weatherTemp = 23;
  String _weatherDescription = 'Clear sky';
  bool _isWeatherLoading = false;

  @override
  void initState() {
    super.initState();
    _fetchLiveWeather();
  }

  Future<void> _fetchLiveWeather() async {
    if (!mounted) return;
    setState(() => _isWeatherLoading = true);
    try {
      final weatherService = WeatherService();
      final weather = await weatherService.getCurrentWeather();
      if (!mounted) return;
      setState(() {
        _weatherCity = weather['city'] as String? ?? 'Local Area';
        _weatherTemp = weather['temp'] as int? ?? 23;
        _weatherDescription =
            weather['description'] as String? ?? 'Clear sky';
      });
    } catch (e) {
      debugPrint('Weather fetch error: $e');
    } finally {
      if (mounted) setState(() => _isWeatherLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final trending = widget.places.take(5).toList();
    final greeting =
        'Namaste,\n${UserSession.loggedInUser ?? 'Explorer'}';

    return Scaffold(
      backgroundColor: kCream,
      body: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: _buildHeader(context, greeting),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: _buildSearchBar(context),
            ),
          ),
          SliverToBoxAdapter(child: const SizedBox(height: 24)),
          SliverToBoxAdapter(
              child: _buildAIPlannerHero(context)),
          SliverToBoxAdapter(child: const SizedBox(height: 20)),
          SliverToBoxAdapter(
              child: _buildWeatherAndFeatured(context)),
          SliverToBoxAdapter(child: const SizedBox(height: 28)),
          SliverToBoxAdapter(
              child: _buildTrendingSection(context, trending)),
          SliverToBoxAdapter(child: const SizedBox(height: 28)),
          SliverToBoxAdapter(
              child: _buildCommunitySection(context)),
          SliverToBoxAdapter(child: const SizedBox(height: 100)),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context, String greeting) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
          20, MediaQuery.of(context).padding.top + 20, 20, 16),
      child: Row(
        children: [
          Expanded(
            child: Text(
              greeting,
              style: Theme.of(context).textTheme.displayMedium,
            ),
          ),
          CircleAvatar(
            radius: 22,
            backgroundColor: kOrange,
            child: Text(
              UserSession.initials(
                  UserSession.loggedInUser),
              style: GoogleFonts.inter(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                  fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchBar(BuildContext context) {
    return GestureDetector(
      onTap: () => widget.onSwitchTab(1),
      child: Container(
        padding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(30),
          border: Border.all(color: kBorder),
        ),
        child: Row(
          children: [
            const Icon(Icons.search, color: kGray, size: 20),
            const SizedBox(width: 10),
            Text('Where do you want to go?',
                style: GoogleFonts.inter(
                    fontSize: 15, color: kGray)),
          ],
        ),
      ),
    );
  }

  Widget _buildAIPlannerHero(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: GestureDetector(
        onTap: () => widget.onSwitchTab(2),
        child: Container(
          height: 240,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF2C5F6E), Color(0xFF1A3A45)],
            ),
          ),
          child: Stack(
            children: [
              Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      const Color(0xFF5B8FA8)
                          .withValues(alpha: 0.6),
                      const Color(0xFF1A3A45)
                          .withValues(alpha: 0.95),
                    ],
                  ),
                ),
              ),
              Positioned(
                top: 20,
                left: 20,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color:
                        Colors.white.withValues(alpha: 0.2),
                    borderRadius:
                        BorderRadius.circular(20),
                    border: Border.all(
                        color: Colors.white
                            .withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.auto_awesome,
                          color: Colors.white, size: 14),
                      const SizedBox(width: 6),
                      Text('AI PLANNER',
                          style: GoogleFonts.inter(
                              color: Colors.white,
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1)),
                    ],
                  ),
                ),
              ),
              Positioned(
                left: 20,
                right: 20,
                bottom: 20,
                child: Column(
                  crossAxisAlignment:
                      CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Plan your next road trip\nwith quiet intelligence.',
                      style: GoogleFonts.playfairDisplay(
                          color: Colors.white,
                          fontSize: 22,
                          fontWeight: FontWeight.w600,
                          height: 1.35),
                    ),
                    const SizedBox(height: 14),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(
                          vertical: 13),
                      decoration: BoxDecoration(
                        color: kOrange,
                        borderRadius:
                            BorderRadius.circular(12),
                      ),
                      child: Row(
                        mainAxisAlignment:
                            MainAxisAlignment.center,
                        children: [
                          const Icon(
                              Icons.auto_awesome,
                              color: Colors.white,
                              size: 18),
                          const SizedBox(width: 8),
                          Text('Start AI Planner',
                              style: GoogleFonts.inter(
                                  color: Colors.white,
                                  fontSize: 15,
                                  fontWeight:
                                      FontWeight.w600)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildWeatherAndFeatured(BuildContext context) {
    return SizedBox(
      height: 110,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        children: [
          WeatherCard(
            city: _weatherCity.toUpperCase(),
            temp: _weatherTemp,
            desc: _weatherDescription,
            isLoading: _isWeatherLoading,
          ),
          const SizedBox(width: 12),
          const FeaturedTripCard(
            name: 'Annapurna Circuit',
            subtitle: '2 days • 1 night',
          ),
        ],
      ),
    );
  }

  Widget _buildTrendingSection(
      BuildContext context, List<Place> trending) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Trending in Nepal',
                  style: Theme.of(context)
                      .textTheme
                      .headlineMedium
                      ?.copyWith(fontSize: 20)),
              TextButton(
                onPressed: () => widget.onSwitchTab(1),
                child: Text('See map',
                    style: GoogleFonts.inter(
                        color: kOrange,
                        fontWeight: FontWeight.w600,
                        fontSize: 14)),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        ...trending.map((place) => TrendingListTile(
              place: place,
              onToggleSave: () => setState(() {
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
            )),
      ],
    );
  }

  Widget _buildCommunitySection(BuildContext context) {
    final list = UserSession.publicItineraries;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('COMMUNITY',
                  style: Theme.of(context)
                      .textTheme
                      .labelLarge),
              const SizedBox(height: 4),
              Text('Itineraries from fellow travelers',
                  style: GoogleFonts.playfairDisplay(
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                      color: kDark,
                      fontStyle: FontStyle.italic)),
            ],
          ),
        ),
        const SizedBox(height: 16),
        if (list.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 20),
            child: Text(
                'No community itineraries shared yet.'),
          )
        else
          ...list.map((it) => CommunityCard(
                itinerary: it,
                onUpdate: () => setState(() {}),
              )),
      ],
    );
  }
}