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

# --- State Management for Expander ---
if "expander_open" not in st.session_state:
    st.session_state.expander_open = True

# --- Google Font Injection & Custom Styling ---
st.markdown("""
    <style>
        /* Force Roboto globally across all Streamlit elements */
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
        
        html, body, [class*="css"], .stText, .stMarkdown, .stButton, input, p, div {
            font-family: 'Roboto', sans-serif !important;
        }

        /* Clean up main container width for a mobile-app feel */
        .main .block-container {
            padding-top: 2rem;
            max-width: 900px;
        }

        /* Styling the Search Button to match Slider Orange-Red (#FF4B4B) */
        div.stButton > button {
            background-color: #FF4B4B !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            padding: 0.5rem 1rem !important;
            transition: 0.3s all ease;
        }
        div.stButton > button:hover {
            background-color: #ff3333 !important;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
            transform: translateY(-1px);
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
    return st.session_state.get("password_correct", False)

if not check_password():
    st.stop()

# --- MAIN APP START ---
st.title("Meetup Triangulator")

# --- Form / Controls at the Top ---
# The 'expanded' state is driven by session_state
with st.expander("Configure Search", expanded=st.session_state.expander_open):
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

# --- Logic Processing ---
if submit_button:
    # 1. Close the expander for the next rerun
    st.session_state.expander_open = False
    
    if not api_key:
        st.error("Google Maps API Key not found.")
    elif not loc_a_text or not loc_b_text:
        st.warning("Please provide both locations.")
        st.session_state.expander_open = True # Re-open if there is an error
        st.rerun()
    else:
        gmaps = googlemaps.Client(key=api_key)
        
        try:
            # 1. Geocode
            geocode_a = gmaps.geocode(loc_a_text)
            geocode_b = gmaps.geocode(loc_b_text)
            
            if not geocode_a or not geocode_b:
                st.error("Could not find one of those addresses.")
                st.session_state.expander_open = True
                st.stop()
                
            coords_a = geocode_a[0]['geometry']['location']
            coords_b = geocode_b[0]['geometry']['location']
            
            # 2. Search (Radius: walk_speed * mins * buffer)
            search_radius = max_mins * 80 * 1.2
            search_terms = selected_cuisines if (selected_cuisines and "Any" not in selected_cuisines) else [None]

            all_venues = []
            with st.spinner("Triangulating..."):
                for term in search_terms:
                    search_args = {"location": coords_a, "radius": search_radius, "type": "restaurant"}
                    if term: search_args["keyword"] = term
                    
                    places_result = gmaps.places_nearby(**search_args)
                    all_venues.extend(places_result.get('results', []))

            unique_venues = {v['place_id']: v for v in all_venues}.values()
            venues = list(unique_venues)

            if not venues:
                st.info("No restaurants found in this area.")
                st.session_state.expander_open = True
            else:
                final_list = []
                chunk_size = 25
                
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
                                maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(venue['name'])}&query_place_id={venue.get('place_id')}"
                                final_list.append({
                                    "Name": venue['name'],
                                    "Rating": rating,
                                    "Mins from A": round(walk_a, 1),
                                    "Mins from B": round(walk_b, 1),
                                    "Link": maps_url, 
                                    "lat": venue['geometry']['location']['lat'],
                                    "lon": venue['geometry']['location']['lng'],
                                    "color_rgb": [255, 75, 75, 200], # Matches slider color
                                    "tooltip_extra": f"Rating: {rating} ⭐"
                                })
                        except: continue

                if not final_list:
                    st.warning("No matches found within that distance for both people.")
                    st.session_state.expander_open = True
                else:
                    # Rerun to collapse the expander visually before drawing results
                    # (This ensures the results appear at the top)
                    st.rerun()

# --- Results Rendering (Outside the submit logic to persist on map) ---
if not st.session_state.expander_open and 'final_list' in locals():
    # If search was successful, final_list exists in this scope
    pass # Search logic continues below...

# Note: In Streamlit, if you want the map to persist after the expander closes, 
# you should store the results in session_state as well. 
# Added that logic below for a seamless experience.

if "results" in st.session_state and not st.session_state.expander_open:
    res = st.session_state.results
    map_data = pd.DataFrame(res['list'])
    
    anchors = pd.DataFrame([
        {"lat": res['coords_a']['lat'], "lon": res['coords_a']['lng'], "Name": "Location A", "color_rgb": [0, 100, 255, 255], "tooltip_extra": ""},
        {"lat": res['coords_b']['lat'], "lon": res['coords_b']['lng'], "Name": "Location B", "color_rgb": [0, 255, 100, 255], "tooltip_extra": ""} 
    ])
    full_map_df = pd.concat([map_data, anchors], ignore_index=True)
    
    st.pydeck_chart(pdk.Deck(
        map_style='light',
        initial_view_state=pdk.ViewState(
            latitude=full_map_df['lat'].mean(),
            longitude=full_map_df['lon'].mean(),
            zoom=13, pitch=0),
        layers=[
            pdk.Layer('ScatterplotLayer', data=full_map_df, get_position='[lon, lat]', 
                      get_color='color_rgb', get_radius=40, pickable=True),
        ],
        tooltip={"text": "{Name}\n{tooltip_extra}"} 
    ))
    
    st.markdown("""
    <div style="display: flex; gap: 20px; font-size: 12px; margin: 10px 0 30px 0; justify-content: center; color: #555;">
        <div><span style="color:#0064FF">●</span> Start A</div>
        <div><span style="color:#00FF64">●</span> Start B</div>
        <div><span style="color:#FF4B4B">●</span> Matching Restaurants</div>
    </div>
    """, unsafe_allow_html=True)
    
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
    
    if st.button("New Search"):
        st.session_state.expander_open = True
        del st.session_state.results
        st.rerun()

# --- Logic to save results into session state ---
if submit_button and 'final_list' in locals() and final_list:
    st.session_state.results = {
        'list': final_list,
        'coords_a': coords_a,
        'coords_b': coords_b
    }
    st.rerun()

elif st.session_state.expander_open:
    st.info("Set your locations and radius above to find the perfect middle ground.")
