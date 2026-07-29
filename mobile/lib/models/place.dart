class Place {
  final String id, name, category;
  final String group;
  final String? wikidataId, wikipediaUrl, website;
  final double? latitude, longitude;
  final Map<String, dynamic>? rawTags;
  final List<String>? semanticTags, travelStyles, bestSeasons, landscape;
  final String? difficulty, visitDuration, accessibility;
  final bool? familyFriendly;
  final double? popularity, rating;
  final String? createdAt, updatedAt;
  
  // Backward compatibility fields — mutable so LLM/UI can enrich after parse
  String? district, province, city, description, history;
  List<String>? images;
  bool? hasTicket;
  List<String>? tags, seasons;
  
  double? distanceKm;
  double? distanceToRouteKm;

  Place({
    required this.id,
    required this.name,
    required this.category,
    this.group = '',
    this.wikidataId,
    this.wikipediaUrl,
    this.website,
    this.latitude,
    this.longitude,
    this.rawTags,
    this.semanticTags,
    this.travelStyles,
    this.bestSeasons,
    this.landscape,
    this.difficulty,
    this.visitDuration,
    this.familyFriendly,
    this.accessibility,
    this.popularity,
    this.rating,
    this.createdAt,
    this.updatedAt,
    // Backward compatibility
    this.district,
    this.province,
    this.city,
    this.description,
    this.history,
    this.images,
    this.hasTicket,
    this.tags,
    this.seasons,
    this.distanceKm,
    this.distanceToRouteKm,
  });

  factory Place.fromJson(Map<String, dynamic> j) {
    final lat = j['latitude'];
    final lng = j['longitude'];
    final rawTagsMap = j['raw_tags'] != null ? Map<String, dynamic>.from(j['raw_tags']) : null;
    
    final latDouble = lat != null ? (lat as num).toDouble() : null;
    final lngDouble = lng != null ? (lng as num).toDouble() : null;

    // Normalize backend field variants: LLM uses poi_id/poi_name, fallback uses poi_id/name
    final id = j['id'] ?? j['poi_id'] ?? '';
    final name = j['name'] ?? j['poi_name'] ?? '';
    String? category = j['category'] as String?;
    // Fallback category inference from activity_type or parent key
    category ??= (j['activity_type'] == 'restaurant' || j['activity_type'] == 'accommodation')
        ? j['activity_type']
        : null;
    if (category == null || category.isEmpty) {
      category = 'Tourist attraction';
    }

    // Debug logging for coordinate parsing
    if (latDouble == 0.0 || lngDouble == 0.0) {
      print('Warning: Place "$name" has invalid coordinates: ($latDouble, $lngDouble)');
    }
    
    return Place(
      id: id,
      name: name,
      category: category,
      group: j['group'] ?? '',
      wikidataId: j['wikidata_id'],
      wikipediaUrl: j['wikipedia_url'],
      website: j['website'],
      latitude: latDouble,
      longitude: lngDouble,
      rawTags: rawTagsMap,
      semanticTags: j['semantic_tags'] != null ? List<String>.from(j['semantic_tags']) : null,
      travelStyles: j['travel_styles'] != null ? List<String>.from(j['travel_styles']) : null,
      bestSeasons: j['best_seasons'] != null ? List<String>.from(j['best_seasons']) : null,
      landscape: j['landscape'] != null ? List<String>.from(j['landscape']) : null,
      difficulty: j['difficulty'],
      visitDuration: j['visit_duration'],
      familyFriendly: j['family_friendly'],
      accessibility: j['accessibility'],
      popularity: j['popularity'] != null ? (j['popularity'] as num).toDouble() : null,
      rating: j['rating'] != null ? (j['rating'] as num).toDouble() : null,
      createdAt: j['created_at'],
      updatedAt: j['updated_at'],
      // Backward compatibility - use provided values or compute from rawTags
      district: j['district'] ?? j['addr:city'] ?? j['addr:district'] ?? rawTagsMap?['addr:city'] ?? rawTagsMap?['addr:district'],
      province: j['province'] ?? j['addr:province'] ?? rawTagsMap?['addr:province'],
      city: j['city'] ?? j['addr:city'] ?? rawTagsMap?['addr:city'],
      description: j['description'] ?? j['tourism'] ?? j['category'] ?? rawTagsMap?['description'] ?? rawTagsMap?['tourism'],
      history: j['history'] ?? j['historic'] ?? rawTagsMap?['historic'],
      images: j['images'] != null ? List<String>.from(j['images']) : null,
      hasTicket: j['has_ticket'],
      tags: j['tags'] != null ? List<String>.from(j['tags']) : (j['semantic_tags'] != null ? List<String>.from(j['semantic_tags']) : null),
      seasons: j['seasons'] != null ? List<String>.from(j['seasons']) : (j['best_seasons'] != null ? List<String>.from(j['best_seasons']) : null),
      distanceKm: j['distance_km'] != null
          ? (j['distance_km'] as num).toDouble()
          : null,
      distanceToRouteKm: j['distance_to_route_km'] != null
          ? (j['distance_to_route_km'] as num).toDouble()
          : null,
    );
  }

  // Safe getters with default values for backward compatibility
  String get imageUrl => (images != null && images!.isNotEmpty) ? images!.first : '';
  double get safeRating => rating ?? 4.0;
  double get safeLatitude => latitude ?? 0.0;
  double get safeLongitude => longitude ?? 0.0;
  String get safeDistrict => district ?? rawTags?['addr:city'] ?? rawTags?['addr:district'] ?? '';
  String get safeProvince => province ?? rawTags?['addr:province'] ?? '';
  String get safeCity => city ?? rawTags?['addr:city'] ?? '';
  String get safeDescription => description ?? rawTags?['description'] ?? rawTags?['tourism'] ?? category;
  String get safeHistory => history ?? rawTags?['historic'] ?? '';
  List<String> get safeImages => images ?? [];
  bool get safeHasTicket => hasTicket ?? false;
  List<String> get safeTags => tags ?? semanticTags ?? [];
  List<String> get safeSeasons => seasons ?? bestSeasons ?? [];
}