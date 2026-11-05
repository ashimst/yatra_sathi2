export interface Activity {
  poi_id?: string;
  name: string;
  poi_name?: string;
  category: string;
  latitude: number;
  longitude: number;
  image_url?: string;
  is_hidden_gem?: boolean;
  must_try?: string;
  price_level?: string;
  start_time?: string;
  end_time?: string;
  duration_hours?: number;
  activity_type?: string;
  description?: string;
  similarity?: number;
}

export interface Meal {
  poi_id?: string;
  name: string;
  category?: string;
  latitude: number;
  longitude: number;
  image_url?: string;
  must_try?: string;
  price_level?: string;
  meal_type: 'lunch' | 'dinner' | string;
  time?: string;
  description?: string;
}

export interface OvernightAccommodation {
  poi_id?: string;
  name: string;
  poi_name?: string;
  category?: string;
  latitude: number;
  longitude: number;
  image_url?: string;
  price_level?: string;
  must_try?: string;
  is_hidden_gem?: boolean;
  description?: string;
}

export interface ItineraryDay {
  day: number;
  starting_location?: string;
  activities: Activity[];
  meals: Meal[];
  overnight_accommodation?: OvernightAccommodation | null;
}

export interface Itinerary {
  days: ItineraryDay[];
  total_days: number;
  pace: string;
  budget: string;
  interests?: string[];
  summary?: string;
  tips?: string[];
}

export interface RouteData {
  distance_km: number;
  duration_minutes: number;
  coordinates: [number, number][]; // [lat, lng]
}

export interface RecommendationResponse {
  route: RouteData;
  itinerary: Itinerary;
  num_days: number;
  travel_style: string;
  budget: string;
  total_pois_found?: number;
}

export interface Place {
  id: string;
  name: string;
  category: string;
  latitude: number;
  longitude: number;
  image_url?: string;
  is_hidden_gem?: boolean;
  must_try?: string;
  price_level?: string;
  district?: string;
  description?: string;
  rating?: number;
  popularity?: number;
}
