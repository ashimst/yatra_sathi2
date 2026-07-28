"""
Test script for the new hybrid recommendation pipeline with category-aware filtering.
"""
import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.app.services.recommendation_service import recommendation_service


async def main():
    """Test the hybrid recommendation pipeline."""
    print("=" * 70)
    print("Testing Hybrid Recommendation Pipeline (Category-Aware)")
    print("=" * 70)
    
    # Test parameters (Kathmandu to Pokhara)
    origin_lat = 27.7172
    origin_lng = 85.3240
    dest_lat = 28.2096
    dest_lng = 83.9856
    
    # User preferences
    interests = ["Nature", "Photography", "Culture"]
    dietary_preferences = ["Veg"]
    num_children = 0
    pace = "balanced"
    budget = "medium"
    travel_season = "spring"
    num_days = 3
    
    print(f"\n[INFO] Route: Kathmandu ({origin_lat}, {origin_lng}) to Pokhara ({dest_lat}, {dest_lng})")
    print(f"[INFO] User Preferences:")
    print(f"  - Interests: {', '.join(interests)}")
    print(f"  - Dietary: {', '.join(dietary_preferences)}")
    print(f"  - Pace: {pace}")
    print(f"  - Budget: {budget}")
    print(f"  - Season: {travel_season}")
    print(f"  - Duration: {num_days} days")
    
    try:
        print("\n[INFO] Starting hybrid recommendation pipeline...")
        print("[INFO] Using mock route data to avoid OSRM API issues")
        
        # Create mock route data for testing
        mock_route_coordinates = [
            [85.3240, 27.7172],  # Kathmandu
            [85.0, 27.8],
            [84.5, 28.0],
            [84.0, 28.1],
            [83.9856, 28.2096]  # Pokhara
        ]
        
        # Test the buffer retrieval
        candidates = recommendation_service._get_pois_in_route_buffer(
            mock_route_coordinates,
            buffer_km=20,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            destination_buffer_km=50
        )
        
        print(f"\n[OK] Found {len(candidates)} candidates in buffer")
        
        # Diagnose category counts after spatial retrieval
        recommendation_service._diagnose_category_counts(candidates, "Spatial retrieval")
        
        # Apply hard filters
        filtered = recommendation_service._apply_hard_filters(
            candidates,
            num_children=num_children,
            dietary_preferences=dietary_preferences,
            budget=budget,
        )
        
        print(f"[OK] After hard filters: {len(filtered)} candidates")
        
        # Diagnose category counts after hard filters
        recommendation_service._diagnose_category_counts(filtered, "After hard filters")
        
        # Test embedding similarity scoring
        scored = recommendation_service._score_candidates(
            filtered,
            interests=interests,
            dietary_preferences=dietary_preferences,
            num_children=num_children,
            budget=budget,
            travel_season=travel_season,
            pace=pace,
            num_days=num_days,
        )
        
        print(f"[OK] After embedding similarity scoring: {len(scored)} candidates")
        
        # Test category-specific retrieval
        print(f"\n[INFO] Testing category-specific retrieval...")
        category_results = recommendation_service._category_specific_retrieval(
            scored,
            num_days=num_days,
            pace=pace
        )
        
        total_filtered = sum(len(v["candidates"]) for v in category_results.values())
        print(f"[OK] After category-specific retrieval: {total_filtered} candidates")
        
        for category, info in category_results.items():
            print(f"  - {category.capitalize()}: requested={info['requested']}, available={info['available']}, selected={info['selected']}")
        
        # Show top results from each category
        print("\n" + "=" * 70)
        print("Top 3 Results by Category")
        print("=" * 70)
        
        for category in ["accommodation", "restaurants", "attractions"]:
            print(f"\n{category.upper()}:")
            for i, dest in enumerate(category_results[category]["candidates"][:3], 1):
                print(f"  {i}. {dest.get('name', 'Unknown')}")
                print(f"     Category: {dest.get('category', 'Unknown')}")
                print(f"     Similarity: {dest.get('embedding_similarity', 0):.4f}")
                print(f"     Distance to Route: {dest.get('distance_to_route_km', 0):.2f}km")
        
        print("\n" + "=" * 70)
        print("[OK] Hybrid pipeline test completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
