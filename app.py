import streamlit as st
import googlemaps
import pydeck as pdk
import pandas as pd
import urllib.parse

# --- Page Config ---
st.set_page_config(
    page_title="Meetup Triangulator", 
    layout="wide"
)

# --- State Management ---
if "expander_open" not in st.session_state:
    st.session_state.expander_open = True
if "results" not in st.session_state:
    st.session_state.results = None

# --- CSS Injection (Clean Roboto & Slider-Matching Button) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
        
        /* Apply Roboto to main text elements without breaking layout components */
        html, body, .stApp, .stMarkdown, .stText, .stButton, .stDataFrame, h1, h2, h3 {
            font-family: 'Roboto', sans-serif !important;
        }

        /* Standardize app width for mobile/tablet feel */
        .main .block-container {
            padding-top: 1.5rem;
            max-width: 900px;
        }

        /* Style Button to match Streamlit's 'Orange-Red' Slider Color (#FF4B4B) */
        /* Targets the button via the 'search_btn' key assigned in Python */
        .st-key-search_btn button {
            background-color: #FF4B4B !important;
            color: white !important;
            border: 1px solid #FF4B4B !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            padding: 0.6rem 1rem !important;
            width: 100% !important;
            transition: 0.2s all ease;
        }
        .st-key-search_btn button:hover {
            background-color: #e64040 !important;
            border-color: #e64040 !important;
            box-shadow: 0 4px 12px rgba(255, 75, 75, 0.3) !important;
        }
        .st-key-search_btn button:active {
            background-color: #cc3939 !important;
        }
    </style>
    """, unsafe_allow_html=True)

# --- Authentication ---
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
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state.get("password_correct", False)

if not check_password():
    st.stop()

# --- APP HEADER ---
st.title("Meetup Triangulator")

# --- SEARCH PANEL ---
with st.expander("Configure Search", expanded=st.session_state.expander_open):
    # API KEY LOGIC
    if "gmaps_api_key" in st.secrets:
        api_key = st.secrets["gmaps_api_key"]
    else:
        api_key = st.text_input("Google Maps API Key", type="password")

    with st.form("search_form", border=False):
        col1, col2 = st.columns(2)
        with col1:
            loc_a_text = st.text_input("First Location", value="")
            max_mins = st.slider("Max Walking Minutes", 5, 30, 15)
        with col2:
            loc_b_text = st.text_input("Second Location", value="")
            min_rating = st.slider("Minimum Rating", 0, 5, 4)

        # FULL RESTORED CUISINE LIST
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
        
        selected_cuisines = st.multiselect("Cuisines (Leave empty for Any)", options=CUISINE_OPTIONS)
        
        # Unique key 'search_btn' used for CSS targeting above
        submit_button = st.form_submit_button("Search Locations", key="search_btn")

# --- LOGIC PROCESSING ---
if submit_button:
    if not api_key:
        st.error("Missing API Key.")
    elif not loc_a_text or not loc_b_text:
        st.warning("Please enter both locations.")
    else:
        gmaps = googlemaps.Client(key=api_key)
        try:
            with st.spinner("Triangulating..."):
                # 1. Geocode
                geo_a = gmaps.geocode(loc_a_text)
                geo_b = gmaps.geocode(loc_b_text)
                
                if not geo_a or not geo_b:
                    st.error("One of the addresses could not be found.")
                else:
                    coords_a = geo_a[0]['geometry']['location']
                    coords_b = geo_b[0]['geometry']['location']
                    
                    # 2. Search Area (walk_speed * mins * slight overlap buffer)
                    search_radius = max_mins * 80 * 1.3
                    search_terms = selected_cuisines if (selected_cuisines and "Any" not in selected_cuisines) else [None]
                    
                    all_venues = []
                    for term in search_terms:
                        res = gmaps.places_nearby(location=coords_a, radius=search_radius, type="restaurant", keyword=term)
                        all_venues.extend(res.get('results', []))
                    
                    # Deduplicate results by Place ID
                    venues = list({v['place_id']: v for v in all_venues}.values())
                    
                    # 3. Filter by Walk Time via Distance Matrix
                    final_list = []
                    if venues:
                        # Process top 25 for efficient single API call
                        venues = venues[:25]
                        chunk_coords = [v['geometry']['location'] for v in venues]
                        dm = gmaps.distance_matrix(origins=[coords_a, coords_b], destinations=chunk_coords, mode="walking")
                        
                        for j, venue in enumerate(venues):
                            rating = venue.get('rating', 0)
                            if rating < min_rating: continue
                            
                            try:
                                # Duration values are in seconds, convert to minutes
                                w_a = dm['rows'][0]['elements'][j]['duration']['value'] / 60
                                w_b = dm['rows'][1]['elements'][j]['duration']['value'] / 60
                                
                                if w_a <= max_mins and w_b <= max_mins:
                                    query = urllib.parse.quote(venue['name'])
                                    maps_url = f"https://www.google.com/maps/search/?api=1&query={query}&query_place_id={venue.get('place_id')}"
                                    final_list.append({
                                        "Name": venue['name'],
                                        "Rating": rating,
                                        "Mins from A": round(w_a, 1),
                                        "Mins from B": round(w_b, 1),
                                        "Link": maps_url, 
                                        "lat": venue['geometry']['location']['lat'],
                                        "lon": venue['geometry']['location']['lng'],
                                        "color_rgb": [255, 75, 75, 200],
                                        "tooltip_extra": f"Rating: {rating} ⭐"
                                    })
                            except (KeyError, IndexError):
                                continue

                    if not final_list:
                        st.warning("No matches found within that walking distance of both locations.")
                    else:
                        st.session_state.results = {
                            "list": final_list,
                            "coords_a": coords_a,
                            "coords_b": coords_b
                        }
                        st.session_state.expander_open = False
                        st.rerun()
        except Exception as e:
            st.error(f"Search failed: {e}")

# --- DISPLAY RESULTS ---
if st.session_state.results and not st.session_state.expander_open:
    res = st.session_state.results
    map_df = pd.DataFrame(res['list'])
    
    # Start and End Markers
    anchors = pd.DataFrame([
        {"lat": res['coords_a']['lat'], "lon": res['coords_a']['lng'], "Name": "Location A", "color_rgb": [0, 100, 255, 255], "tooltip_extra": "Starting Point"},
        {"lat": res['coords_b']['lat'], "lon": res['coords_b']['lng'], "Name": "Location B", "color_rgb": [0, 255, 100, 255], "tooltip_extra": "Starting Point"} 
    ])
    full_df = pd.concat([map_df, anchors], ignore_index=True)

    # Clean Map View
    st.pydeck_chart(pdk.Deck(
        map_style='light',
        initial_view_state=pdk.ViewState(
            latitude=full_df['lat'].mean(),
            longitude=full_df['lon'].mean(),
            zoom=13.5),
        layers=[
            pdk.Layer('ScatterplotLayer', data=full_df, get_position='[lon, lat]', 
                      get_color='color_rgb', get_radius=40, pickable=True),
        ],
        tooltip={"text": "{Name}\n{tooltip_extra}"}
    ))

    # Unified Legend
    st.markdown("""
    <div style="display: flex; gap: 20px; font-size: 13px; margin: 10px 0 30px 0; justify-content: center; color: #666;">
        <div><span style="color:#0064FF">●</span> Start A</div>
        <div><span style="color:#00FF64">●</span> Start B</div>
        <div><span style="color:#FF4B4B">●</span> Restaurants</div>
    </div>
    """, unsafe_allow_html=True)

    # Clean Results Data
    st.dataframe(
        map_df,
        column_order=["Name", "Rating", "Mins from A", "Mins from B", "Link"],
        use_container_width=True, hide_index=True,
        column_config={
            "Link": st.column_config.LinkColumn("Google Maps", display_text="Directions 🔗"),
            "Rating": st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
        }
    )

    # Footer Action
    if st.button("New Search"):
        st.session_state.expander_open = True
        st.session_state.results = None
        st.rerun()

elif st.session_state.expander_open:
    st.info("Find the perfect middle ground between two people.")
