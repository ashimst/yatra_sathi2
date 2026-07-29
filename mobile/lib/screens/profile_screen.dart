import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/services/user_session.dart';
import 'package:mobile/screens/auth_gate.dart';
import 'package:mobile/widgets/ai_chat_widget.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kCream,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const SizedBox(height: 10),
            Center(
              child: Column(
                children: [
                  CircleAvatar(
                    radius: 44,
                    backgroundColor: kOrange,
                    child: Text(
                      UserSession.initials(
                          UserSession.loggedInUser),
                      style: GoogleFonts.inter(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                          fontSize: 24),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                      UserSession.loggedInUser ??
                          'Explorer',
                      style: GoogleFonts.inter(
                          fontSize: 20,
                          fontWeight: FontWeight.w700,
                          color: kDark)),
                  const SizedBox(height: 4),
                  Text(
                      UserSession.email ??
                          'guest@yatrasathi.com',
                      style: GoogleFonts.inter(
                          fontSize: 13, color: kGray)),
                ],
              ),
            ),
            const SizedBox(height: 28),
            Row(
              children: [
                _statCard('Trips Created',
                    '${UserSession.savedItineraries.length}'),
                const SizedBox(width: 12),
                _statCard('Places Saved',
                    '${UserSession.savedPlaceIds.length}'),
                const SizedBox(width: 12),
                _statCard('Community Trips',
                    '${UserSession.publicItineraries.length}'),
              ],
            ),
            const SizedBox(height: 28),
            Text('SETTINGS',
                style: Theme.of(context)
                    .textTheme
                    .labelLarge),
            const SizedBox(height: 12),
            ...[
              ('Preferences', Icons.tune_outlined),
              ('Notifications',
                  Icons.notifications_outlined),
              ('Language', Icons.language_outlined),
              ('Currency',
                  Icons.currency_rupee_outlined),
              ('Privacy', Icons.lock_outline),
              ('Logout', Icons.logout),
            ].map((item) => Material(
                  color: Colors.transparent,
                  child: Container(
                    margin:
                        const EdgeInsets.only(bottom: 6),
                    decoration: BoxDecoration(
                        color: kCardBg,
                        borderRadius:
                            BorderRadius.circular(12),
                        border: Border.all(
                            color: kBorder)),
                    child: ClipRRect(
                      borderRadius:
                          BorderRadius.circular(12),
                      child: ListTile(
                        tileColor: kCardBg,
                        leading: Icon(item.$2,
                            color: item.$1 == 'Logout'
                                ? kOrange
                                : kGray,
                            size: 20),
                        title: Text(item.$1,
                            style: GoogleFonts.inter(
                                fontSize: 14,
                                fontWeight:
                                    FontWeight.w500,
                                color: kDark)),
                        trailing: const Icon(
                            Icons.chevron_right,
                            color: kGray,
                            size: 20),
                        onTap: () {
                          if (item.$1 == 'Logout') {
                            UserSession
                                .clearSessionOnLogout();
                            Navigator
                                .pushReplacement(
                                    context,
                                    MaterialPageRoute(
                                        builder: (_) =>
                                            const AuthGate()));
                          }
                        },
                      ),
                    ),
                  ),
                )),
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
              screenContext: 'profile',
              screenData: {
                'username': UserSession.loggedInUser,
                'email': UserSession.email,
              },
            ),
          );
        },
        backgroundColor: kOrange,
        child: const Icon(Icons.smart_toy, color: Colors.white),
      ),
    );
  }

  Widget _statCard(String label, String value) =>
      Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(
              vertical: 14),
          decoration: BoxDecoration(
              color: kCardBg,
              borderRadius:
                  BorderRadius.circular(14),
              border: Border.all(color: kBorder)),
          child: Column(children: [
            Text(value,
                style: GoogleFonts.inter(
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                    color: kOrange)),
            const SizedBox(height: 2),
            Text(label,
                style: GoogleFonts.inter(
                    fontSize: 11, color: kGray),
                textAlign: TextAlign.center),
          ]),
        ),
      );
}