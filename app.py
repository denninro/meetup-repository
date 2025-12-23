import streamlit as st
import googlemaps
import pydeck as pdk
import pandas as pd
import time
import urllib.parse

# --- Page Config ---
st.set_page_config(
    page_title="Meetup Triangulator", 
    layout="wide"
)

# --- Google Font Injection & UI Tweaks ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
        }

        /* Make the app feel more mobile-responsive */
        .main .block-container {
            padding-top: 2rem;
            max-width: 800px;
        }
        
        /* Clean up expander styling */
        .streamlit-expanderHeader {
            font-weight: 500;
            background-color: #f8f9fa;
        }
    </style>
    """, unsafe_allow_html=True)

# --- Authentication Logic ---
def check_password():
    if "app_password" not in st.secrets:
        return True

    def password_entered():
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Please enter the app password:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Please enter the app password:", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- MAIN APP START ---
st.title("Meetup Triangulator")

# --- Form / Controls at the Top ---
with st.expander("Configure Search", expanded=True):
    # Use columns for a cleaner layout on desktop, stacks on mobile
    col1, col2 = st.columns(2)
    
    # API KEY LOGIC
    if "gmaps_api_key" in st.secrets:
        api_key = st.secrets["gmaps_api_key"]
    else:
        api_key = st.text_input("Google Maps API Key", type="password")

    with st.form("search_form", border=False):
        with col1:
            loc_a_text = st.text_input("First Location", value="")
            max_mins = st.slider("Max Walking Minutes", 5, 30, 15)
            
        with col2:
            loc_b_text = st.text_input("Second Location", value="")
            min_rating = st.slider("Minimum Rating", 0, 5, 4)

        CUISINE_OPTIONS = [
            "Any", "American", "Asian Fusion", "Bagels", "Bakery", "Bar", "Barbecue", 
            "Breakfast", "Brunch", "Burgers", "Cafe", "Chinese", "Coffee", "Deli", 
            "Dessert", "Diner", "Greek", "Halal", "Indian", "Italian", "Japanese", 
            "Korean", "Mexican", "Middle Eastern", "Pizza", "Salad", "Sandwiches", 
            "Seafood", "Sushi", "Thai", "Vegan", "Vietnamese"
        ]
        
        selected_cuisines = st.multiselect("Cuisines", options=CUISINE_OPTIONS, default=[])
        
        submit_button = st.form_submit_button("Search Locations", use_container_width=True)

# --- Logic ---
if submit_button:
    if not api_key:
        st.error("Google Maps API Key not found.")
    elif not loc_a_text or not loc_b_text:
        st.warning("Please provide both locations.")
    else:
        gmaps = googlemaps.Client(key=api_key)
        
        try:
            # 1. Geocode
            geocode_a = gmaps.geocode(loc_a_text)
            geocode_b = gmaps.geocode(loc_b_text)
            
            if not geocode_a or not geocode_b:
                st.error("Could not find one of those addresses.")
                st.stop()
                
            coords_a = geocode_a[0]['geometry']['location']
            coords_b = geocode_b[0]['geometry']['location']
            
            # 2. Search
            search_radius = max_mins * 80 * 1.2
            search_terms = selected_cuisines if (selected_cuisines and "Any" not in selected_cuisines) else [None]

            all_venues = []
            with st.spinner("Searching..."):
                for term in search_terms:
                    search_args = {"location": coords_a, "radius": search_radius, "type": "restaurant"}
                    if term: search_args["keyword"] = term
                    
                    places_result = gmaps.places_nearby(**search_args)
                    all_venues.extend(places_result.get('results', []))

            # Deduplicate
            unique_venues = {v['place_id']: v for v in all_venues}.values()
            venues = list(unique_venues)

            if not venues:
                st.info("No restaurants found in this area.")
            else:
                final_list = []
                chunk_size = 25
                
                with st.spinner("Calculating convenient meetups..."):
                    for i in range(0, len(venues), chunk_size):
                        chunk = venues[i:i + chunk_size]
                        chunk_coords = [v['geometry']['location'] for v in chunk]
                        
                        dm_result = gmaps.distance_matrix(
                            origins=[coords_a, coords_b],
                            destinations=chunk_coords,
                            mode="walking"
                        )
                        
                        for j, venue in enumerate(chunk):
                            try:
                                rating = venue.get('rating', 0)
                                if rating < min_rating: continue

                                walk_a = dm_result['rows'][0]['elements'][j]['duration']['value'] / 60
                                walk_b = dm_result['rows'][1]['elements'][j]['duration']['value'] / 60
                                
                                if walk_a <= max_mins and walk_b <= max_mins:
                                    place_id = venue.get('place_id')
                                    encoded_name = urllib.parse.quote(venue['name'])
                                    maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded_name}&query_place_id={place_id}"

                                    final_list.append({
                                        "Name": venue['name'],
                                        "Rating": rating,
                                        "Mins from A": round(walk_a, 1),
                                        "Mins from B": round(walk_b, 1),
                                        "Link": maps_url, 
                                        "lat": venue['geometry']['location']['lat'],
                                        "lon": venue['geometry']['location']['lng'],
                                        "color_rgb": [255, 50, 50, 200],
                                        "tooltip_extra": f"Rating: {rating} ⭐" # Info for hover
                                    })
                            except: continue

                if not final_list:
                    st.warning("No venues found within that walking distance of both people.")
                else:
                    map_data = pd.DataFrame(final_list)
                    
                    anchors = pd.DataFrame([
                        {"lat": coords_a['lat'], "lon": coords_a['lng'], "Name": "Location A", "color_rgb": [0, 100, 255, 255], "tooltip_extra": ""},
                        {"lat": coords_b['lat'], "lon": coords_b['lng'], "Name": "Location B", "color_rgb": [0, 255, 100, 255], "tooltip_extra": ""} 
                    ])
                    full_map_df = pd.concat([map_data, anchors], ignore_index=True)
                    
                    # --- MAP SECTION ---
                    st.pydeck_chart(pdk.Deck(
                        map_style='light',
                        initial_view_state=pdk.ViewState(
                            latitude=full_map_df['lat'].mean(),
                            longitude=full_map_df['lon'].mean(),
                            zoom=13, pitch=0),
                        layers=[
                            pdk.Layer(
                                'ScatterplotLayer',
                                data=full_map_df,
                                get_position='[lon, lat]',
                                get_color='color_rgb',
                                get_radius=40,
                                pickable=True),
                        ],
                        tooltip={"text": "{Name}\n{tooltip_extra}"} 
                    ))
                    
                    # Custom Legend
                    st.markdown("""
                    <div style="display: flex; gap: 20px; font-size: 12px; margin: 10px 0 30px 0; justify-content: center;">
                        <div><span style="color:#0064FF">●</span> Start A</div>
                        <div><span style="color:#00FF64">●</span> Start B</div>
                        <div><span style="color:#FF3232">●</span> Restaurants</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Table
                    st.dataframe(
                        map_data,
                        column_order=["Name", "Rating", "Mins from A", "Mins from B", "Link"],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Link": st.column_config.LinkColumn("Google Maps", display_text="Directions 🔗"),
                            "Rating": st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
                        }
                    )
                    
        except Exception as e:
            st.error(f"Error: {e}")

elif not submit_button:
    st.info("Set your locations and radius above to find the perfect middle ground.")
