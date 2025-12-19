import streamlit as st
import googlemaps
import pydeck as pdk
import pandas as pd
import time
import urllib.parse

import streamlit as st
# ... other imports ...

# ADD THESE LINES TEMPORARILY:
st.write("Debug Mode: Keys found in secrets:")
st.write(list(st.secrets.keys()))

# --- Page Config ---
st.set_page_config(page_title="Convenient Meetup Finder", layout="wide")
st.title("📍 Dual-Location Restaurant Finder")
st.markdown("Find restaurants within a specific walking radius of **two** different locations.")
st.caption("Note: The map shows locations. To view details, click the links in the table below.")

# --- Comprehensive Cuisine List ---
CUISINE_OPTIONS = [
    "Any", "American", "Asian Fusion", "Bagels", "Bakery", "Bar", "Barbecue", 
    "Breakfast", "Brunch", "Burgers", "Cafe", "Cajun", "Caribbean", "Chinese", 
    "Cocktails", "Coffee", "Deli", "Dessert", "Dim Sum", "Diner", "Donuts", 
    "Ethiopian", "Fast Food", "Filipino", "French", "German", "Greek", "Halal", 
    "Ice Cream", "Indian", "Indonesian", "Irish", "Italian", "Japanese", "Korean", 
    "Latin American", "Mediterranean", "Mexican", "Middle Eastern", "Noodles", 
    "Pizza", "Poke", "Pub", "Ramen", "Salad", "Sandwiches", "Seafood", "Soup", 
    "Southern", "Spanish", "Steakhouse", "Sushi", "Tacos", "Tapas", "Tea", 
    "Thai", "Vegan", "Vegetarian", "Vietnamese", "Wine Bar", "Wings"
]

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("Settings")
    # Check if the key exists in the secrets (Cloud), otherwise ask for it (Local testing)
    if "gmaps_api_key" in st.secrets:
        api_key = st.secrets["gmaps_api_key"]
    else:
        api_key = st.text_input("Google Maps API Key", type="password")
    
    with st.form("search_form"):
        loc_a_text = st.text_input("First Location (e.g., Home)", value="")
        loc_b_text = st.text_input("Second Location (e.g., Work)", value="")
        
        # SLIDERS (Integers Only)
        max_mins = st.slider("Max Walking Minutes from BOTH locations", 5, 30, 15)
        min_rating = st.slider("Minimum Rating (0-5)", 0, 5, 4)
        
        # MULTI-SELECT WIDGET
        selected_cuisines = st.multiselect(
            "Select Cuisines (Leave empty for Any)", 
            options=CUISINE_OPTIONS,
            default=[]
        )
        
        submit_button = st.form_submit_button("Find Restaurants")

# --- Logic ---
if submit_button:
    if not api_key:
        st.error("Please enter a Google Maps API Key.")
    elif not loc_a_text or not loc_b_text:
        st.error("Please provide both Location A and Location B.")
    else:
        gmaps = googlemaps.Client(key=api_key)
        
        try:
            # 1. Geocode Locations
            geocode_a = gmaps.geocode(loc_a_text)
            geocode_b = gmaps.geocode(loc_b_text)
            
            if not geocode_a or not geocode_b:
                st.error("Could not geocode one or both locations. Please be more specific.")
                st.stop()
                
            coords_a = geocode_a[0]['geometry']['location']
            coords_b = geocode_b[0]['geometry']['location']
            
            # 2. Search for Restaurants
            search_radius = max_mins * 80 * 1.2
            
            # Handle "Any" or Empty selection
            if not selected_cuisines or "Any" in selected_cuisines:
                search_terms = [None] # None means no keyword filter
            else:
                search_terms = selected_cuisines

            all_venues = []
            
            with st.spinner("Fetching locations from Google..."):
                # Loop through EACH selected cuisine
                for term in search_terms:
                    search_args = {
                        "location": coords_a,
                        "radius": search_radius,
                        "type": "restaurant"
                    }
                    if term:
                        search_args["keyword"] = term
                    
                    # Page 1
                    places_result = gmaps.places_nearby(**search_args)
                    current_batch = places_result.get('results', [])
                    all_venues.extend(current_batch)
                    
                    # Pagination (Get up to 60 results per cuisine term)
                    next_token = places_result.get('next_page_token')
                    while next_token:
                        time.sleep(2) 
                        places_result = gmaps.places_nearby(page_token=next_token)
                        current_batch = places_result.get('results', [])
                        all_venues.extend(current_batch)
                        next_token = places_result.get('next_page_token')

            # Deduplicate
            unique_venues = {v['place_id']: v for v in all_venues}.values()
            venues = list(unique_venues)

            if not venues:
                st.warning(f"No restaurants found within {search_radius}m of Location A matching your criteria.")
            else:
                # 3. Filter using Distance Matrix
                final_list = []
                chunk_size = 25
                
                with st.spinner(f"Calculating walking times for {len(venues)} venues..."):
                    for i in range(0, len(venues), chunk_size):
                        chunk = venues[i:i + chunk_size]
                        chunk_coords = [v['geometry']['location'] for v in chunk]
                        
                        try:
                            dm_result = gmaps.distance_matrix(
                                origins=[coords_a, coords_b],
                                destinations=chunk_coords,
                                mode="walking"
                            )
                            
                            for j, venue in enumerate(chunk):
                                try:
                                    rating = venue.get('rating', 0)
                                    if rating < min_rating:
                                        continue

                                    walk_to_a_secs = dm_result['rows'][0]['elements'][j]['duration']['value']
                                    walk_to_b_secs = dm_result['rows'][1]['elements'][j]['duration']['value']
                                    
                                    walk_to_a_mins = round(walk_to_a_secs / 60, 1)
                                    walk_to_b_mins = round(walk_to_b_secs / 60, 1)
                                    
                                    if walk_to_a_mins <= max_mins and walk_to_b_mins <= max_mins:
                                        # Construct URL
                                        place_id = venue.get('place_id')
                                        encoded_name = urllib.parse.quote(venue['name'])
                                        maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded_name}&query_place_id={place_id}"

                                        final_list.append({
                                            "Name": venue['name'],
                                            "Rating": rating,
                                            "Address": venue.get('vicinity', 'N/A'),
                                            "lat": venue['geometry']['location']['lat'],
                                            "lon": venue['geometry']['location']['lng'],
                                            "Mins from Loc A": walk_to_a_mins,
                                            "Mins from Loc B": walk_to_b_mins,
                                            "Link": maps_url, 
                                            "color_rgb": [255, 50, 50, 160] 
                                        })
                                except (KeyError, IndexError):
                                    continue
                        except Exception as e:
                            st.error(f"Error processing batch: {e}")
                            continue

                # 4. Display Results
                if not final_list:
                    st.info(f"Found {len(venues)} nearby, but none matched criteria (Rating > {min_rating} & Walk < {max_mins}).")
                else:
                    map_data = pd.DataFrame(final_list)
                    
                    anchors = pd.DataFrame([
                        {"lat": coords_a['lat'], "lon": coords_a['lng'], "Name": "Location A", "color_rgb": [0, 100, 255, 200]},
                        {"lat": coords_b['lat'], "lon": coords_b['lng'], "Name": "Location B", "color_rgb": [0, 255, 100, 200]} 
                    ])
                    full_map_df = pd.concat([map_data, anchors], ignore_index=True)
                    
                    st.subheader(f"Found {len(final_list)} Matching Venues")
                    
                    # --- MAP SECTION (Now with Light Mode) ---
                    st.pydeck_chart(pdk.Deck(
                        map_style='light', # <--- THIS FIXES THE DARK MODE
                        initial_view_state=pdk.ViewState(
                            latitude=full_map_df['lat'].mean(),
                            longitude=full_map_df['lon'].mean(),
                            zoom=14, pitch=0),
                        layers=[
                            pdk.Layer(
                                'ScatterplotLayer',
                                data=full_map_df,
                                get_position='[lon, lat]',
                                get_color='color_rgb',
                                get_radius=30,
                                pickable=True),
                        ],
                        tooltip={"text": "{Name}\nRating: {Rating}"} 
                    ))
                    
                    st.markdown("""
                    <div style="display: flex; gap: 20px; font-size: 14px; margin-bottom: 20px;">
                        <div><span style="color:blue">●</span> Location A</div>
                        <div><span style="color:green">●</span> Location B</div>
                        <div><span style="color:red">●</span> Restaurant</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("### 📋 Restaurant Details")
                    st.dataframe(
                        map_data,
                        column_order=["Name", "Rating", "Mins from Loc A", "Mins from Loc B", "Link"],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Link": st.column_config.LinkColumn("Google Maps", display_text="Open Map 🔗"),
                            "Rating": st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
                            "Mins from Loc A": st.column_config.NumberColumn("Mins from A", format="%.1f min"),
                            "Mins from Loc B": st.column_config.NumberColumn("Mins from B", format="%.1f min")
                        }
                    )
                    
        except Exception as e:
            st.error(f"An error occurred: {e}")

if not submit_button:
    st.info("Enter your API key and locations to start.")