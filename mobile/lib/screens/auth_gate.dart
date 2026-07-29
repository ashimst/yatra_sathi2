import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/services/user_session.dart';
import 'package:mobile/screens/root_shell.dart';

class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  bool _isLogin = true;
  final _emailController = TextEditingController();
  final _nameController = TextEditingController();
  final _passwordController = TextEditingController();

  void _submit() {
    if (_emailController.text.isEmpty || _passwordController.text.isEmpty) return;
    if (!_isLogin && _nameController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter your name')),
      );
      return;
    }

    setState(() {
      UserSession.loggedInUser = _isLogin
          ? _emailController.text.split('@').first
          : _nameController.text.trim();
      UserSession.email = _emailController.text;
    });
    UserSession.persist();

    Navigator.pushReplacement(
        context, MaterialPageRoute(builder: (_) => const RootShell()));
  }

  void _guestLogin() {
    setState(() {
      UserSession.loggedInUser = 'Guest Explorer';
      UserSession.email = 'guest@yatrasathi.com';
    });
    UserSession.persist();
    Navigator.pushReplacement(
        context, MaterialPageRoute(builder: (_) => const RootShell()));
  }

  @override
  void dispose() {
    _emailController.dispose();
    _nameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kCream,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Yatra Sathi',
                  style: Theme.of(context).textTheme.displayLarge,
                  textAlign: TextAlign.center),
              const SizedBox(height: 8),
              Text('Nepal road trips, curated and designed.',
                  style: Theme.of(context).textTheme.bodyMedium,
                  textAlign: TextAlign.center),
              const SizedBox(height: 36),
              if (!_isLogin) ...[
                TextField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                      labelText: 'Name',
                      hintText: 'Enter your full name'),
                ),
                const SizedBox(height: 12),
              ],
              TextField(
                controller: _emailController,
                decoration: const InputDecoration(
                    labelText: 'Email Address',
                    hintText: 'you@example.com'),
                keyboardType: TextInputType.emailAddress,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _passwordController,
                decoration: const InputDecoration(
                    labelText: 'Password', hintText: '••••••••'),
                obscureText: true,
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: _submit,
                child: Text(_isLogin ? 'Sign In' : 'Sign Up'),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () => setState(() => _isLogin = !_isLogin),
                child: Text(
                    _isLogin
                        ? "Don't have an account? Sign Up"
                        : 'Already have an account? Sign In',
                    style: GoogleFonts.inter(
                        color: kOrange, fontWeight: FontWeight.w600)),
              ),
              const Divider(height: 32, color: kBorder),
              OutlinedButton(
                onPressed: _guestLogin,
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: kBorder),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
                child: Text('Continue as Guest',
                    style: GoogleFonts.inter(
                        color: kDark, fontWeight: FontWeight.w600)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}