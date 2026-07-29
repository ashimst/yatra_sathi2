import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/models/place.dart';
import 'package:mobile/services/place_service.dart';
import 'package:mobile/screens/home_screen.dart';
import 'package:mobile/screens/explore_screen.dart';
import 'package:mobile/screens/plan_screen.dart';
import 'package:mobile/screens/saved_screen.dart';
import 'package:mobile/screens/profile_screen.dart';

class RootShell extends StatefulWidget {
  const RootShell({super.key});

  @override
  State<RootShell> createState() => _RootShellState();
}

class _RootShellState extends State<RootShell> {
  int _index = 0;
  List<Place> _places = [];
  bool _placesLoading = true;
  String? _placesError;

  @override
  void initState() {
    super.initState();
    _loadPlaces();
  }

  Future<void> _loadPlaces() async {
    if (!mounted) return;
    setState(() {
      _placesLoading = true;
      _placesError = null;
    });
    try {
      final service = PlaceService();
      final places = await service.fetchPlaces();
      if (!mounted) return;
      setState(() {
        _places = places;
        _placesLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _placesError = 'Could not load places';
        _placesLoading = false;
      });
    }
  }

  void _switchTab(int index) => setState(() => _index = index);

  @override
  Widget build(BuildContext context) {
    final screens = [
      HomeScreen(places: _places, onSwitchTab: _switchTab),
      ExploreScreen(places: _places),
      PlanScreen(places: _places),
      SavedScreen(places: _places),
      const ProfileScreen(),
    ];

    return Scaffold(
      body: _placesLoading
          ? const Center(
              child: CircularProgressIndicator(color: kOrange))
          : _placesError != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(_placesError!,
                          style: GoogleFonts.inter(color: kGray)),
                      const SizedBox(height: 12),
                      ElevatedButton(
                          onPressed: _loadPlaces,
                          child: const Text('Retry')),
                    ],
                  ),
                )
              : IndexedStack(index: _index, children: screens),
      bottomNavigationBar: _buildBottomNav(),
      floatingActionButton: _index != 2
          ? FloatingActionButton(
              onPressed: () => _switchTab(2),
              backgroundColor: kOrange,
              elevation: 4,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(18)),
              child:
                  const Icon(Icons.add, color: Colors.white, size: 28),
            )
          : null,
      floatingActionButtonLocation:
          FloatingActionButtonLocation.centerDocked,
    );
  }

  Widget _buildBottomNav() {
    return Container(
      decoration: const BoxDecoration(
        color: kCardBg,
        border: Border(top: BorderSide(color: kBorder)),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            children: [
              _navItem(0, Icons.home_outlined, Icons.home, 'HOME'),
              _navItem(
                  1, Icons.explore_outlined, Icons.explore, 'EXPLORE'),
              const SizedBox(width: 72),
              _navItem(
                  3, Icons.bookmark_outline, Icons.bookmark, 'SAVED'),
              _navItem(4, Icons.person_outline, Icons.person, 'PROFILE'),
            ],
          ),
        ),
      ),
    );
  }

  Widget _navItem(int index, IconData off, IconData on, String label) {
    final active = _index == index;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _index = index),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(active ? on : off,
                color: active ? kOrange : kGray, size: 24),
            const SizedBox(height: 2),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 10,
                fontWeight: active ? FontWeight.w700 : FontWeight.w400,
                color: active ? kOrange : kGray,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}