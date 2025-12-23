import streamlit as st
import googlemaps
import pydeck as pdk
import pandas as pd
import urllib.parse
from streamlit_searchbox import st_searchbox
from streamlit_js_eval import streamlit_js_eval

# --- Page Config ---
st.set_page_config(page_title="Meetup Triangulator", layout="wide")

# --- State Management ---
if "expander_open" not in st.session_state:
    st.session_state.expander_open = True
if "results" not in st.session_state:
    st.session_state.results = None

# --- CSS Injection ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
        html, body, .stApp, .stMarkdown, .stText, .stButton, .stDataFrame, h1, h2, h3 {
            font-family: 'Roboto', sans-serif !important;
        }
        .st-key-search_btn button {
            background-color: #FF4B4B !important;
            color: white !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            width: 100% !important;
        }
    </style>
    """, unsafe_allow_html=True)

# --- API KEY ---
if "gmaps_api_key" in st.secrets:
    api_key = st.secrets["gmaps_api_key"]
else:
    api_key = st.sidebar.text_input("Google Maps API Key", type="password")

# --- HELPERS ---
def get_address_suggestions(search_term: str):
    """Fetches real-time address suggestions from Google."""
    if not search_term or not api_key:
        return []
    gmaps = googlemaps.Client(key=api_key)
    # Use places_autocomplete for the type-ahead feel
    predictions = gmaps.places_autocomplete(input_text=search_term, types="address")
    return [p['description'] for p in predictions]

# --- MAIN APP ---
st.title("Meetup Triangulator")

with st.expander("Configure Search", expanded=st.session_state.expander_open):
    
    # Current Location Detector
    gps_location = None
    if st.button("🌐 Use My Current Location"):
        # This triggers browser GPS
        loc = streamlit_js_eval(js_expressions='navigator.geolocation.getCurrentPosition', want_output=True)
        if loc:
            gps_location = f"{loc['coords']['latitude']}, {loc['coords']['longitude']}"
            st.success("Location captured!")

    with st.form("search_form", border=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**First Location**")
            # Predictive input for Location A
            loc_a_text = st_searchbox(
                get_address_suggestions,
                key="loc_a",
                placeholder=gps_location if gps_location else "Search address..."
            )
            max_mins = st.slider("Max Walking Minutes", 5, 30, 15)
            
        with col2:
            st.write("**Second Location**")
            # Predictive input for Location B
            loc_b_text = st_searchbox(
                get_address_suggestions,
                key="loc_b",
                placeholder="Work, gym, etc..."
            )
            min_rating = st.slider("Minimum Rating", 0, 5, 4)

        CUISINE_OPTIONS = ["Any", "American", "Asian Fusion", "Barbecue", "Breakfast", "Burgers", "Cafe", "Chinese", "Cocktails", "Coffee", "Deli", "Greek", "Indian", "Italian", "Japanese", "Korean", "Mexican", "Middle Eastern", "Pizza", "Salad", "Sandwiches", "Seafood", "Sushi", "Thai", "Vegan", "Vietnamese"]
        selected_cuisines = st.multiselect("Cuisines", options=CUISINE_OPTIONS)
        
        submit_button = st.form_submit_button("Search Locations", key="search_btn")

# --- LOGIC ---
if submit_button:
    # Use GPS value if user didn't type an address
    final_a = loc_a_text if loc_a_text else gps_location

    if not api_key:
        st.error("Missing API Key.")
    elif not final_a or not loc_b_text:
        st.warning("Please select locations from the predictive dropdowns.")
    else:
        gmaps = googlemaps.Client(key=api_key)
        try:
            with st.spinner("Triangulating..."):
                geo_a = gmaps.geocode(final_a)
                geo_b = gmaps.geocode(loc_b_text)
                
                if geo_a and geo_b:
                    coords_a = geo_a[0]['geometry']['location']
                    coords_b = geo_b[0]['geometry']['location']
                    
                    search_radius = max_mins * 80 * 1.3
                    search_terms = selected_cuisines if (selected_cuisines and "Any" not in selected_cuisines) else [None]
                    
                    all_venues = []
                    for term in search_terms:
                        res = gmaps.places_nearby(location=coords_a, radius=search_radius, type="restaurant", keyword=term)
                        all_venues.extend(res.get('results', []))
                    
                    venues = list({v['place_id']: v for v in all_venues}.values())[:25]
                    final_list = []
                    
                    if venues:
                        chunk_coords = [v['geometry']['location'] for v in venues]
                        dm = gmaps.distance_matrix(origins=[coords_a, coords_b], destinations=chunk_coords, mode="walking")
                        
                        for j, venue in enumerate(venues):
                            rating = venue.get('rating', 0)
                            if rating < min_rating: continue
                            try:
                                w_a = dm['rows'][0]['elements'][j]['duration']['value'] / 60
                                w_b = dm['rows'][1]['elements'][j]['duration']['value'] / 60
                                if w_a <= max_mins and w_b <= max_mins:
                                    query = urllib.parse.quote(venue['name'])
                                    maps_url = f"https://www.google.com/maps/search/?api=1&query={query}&query_place_id={venue.get('place_id')}"
                                    final_list.append({
                                        "Name": venue['name'], "Rating": rating, "Mins from A": round(w_a, 1),
                                        "Mins from B": round(w_b, 1), "Link": maps_url, 
                                        "lat": venue['geometry']['location']['lat'], "lon": venue['geometry']['location']['lng'],
                                        "color_rgb": [255, 75, 75, 200], "tooltip_extra": f"Rating: {rating} ⭐"
                                    })
                            except: continue

                    if final_list:
                        st.session_state.results = {"list": final_list, "coords_a": coords_a, "coords_b": coords_b}
                        st.session_state.expander_open = False
                        st.rerun()
                    else:
                        st.warning("No matches found within that distance.")
        except Exception as e:
            st.error(f"Search failed: {e}")

# --- PERSISTENT RESULTS ---
if st.session_state.results and not st.session_state.expander_open:
    res = st.session_state.results
    map_df = pd.DataFrame(res['list'])
    anchors = pd.DataFrame([
        {"lat": res['coords_a']['lat'], "lon": res['coords_a']['lng'], "Name": "Location A", "color_rgb": [0, 100, 255, 255], "tooltip_extra": "Start"},
        {"lat": res['coords_b']['lat'], "lon": res['coords_b']['lng'], "Name": "Location B", "color_rgb": [0, 255, 100, 255], "tooltip_extra": "Start"} 
    ])
    full_df = pd.concat([map_df, anchors], ignore_index=True)

    st.pydeck_chart(pdk.Deck(
        map_style='light',
        initial_view_state=pdk.ViewState(latitude=full_df['lat'].mean(), longitude=full_df['lon'].mean(), zoom=13.5),
        layers=[pdk.Layer('ScatterplotLayer', data=full_df, get_position='[lon, lat]', get_color='color_rgb', get_radius=40, pickable=True)],
        tooltip={"text": "{Name}\n{tooltip_extra}"}
    ))

    st.dataframe(map_df, column_order=["Name", "Rating", "Mins from A", "Mins from B", "Link"], use_container_width=True, hide_index=True,
        column_config={"Link": st.column_config.LinkColumn("Google Maps", display_text="Directions 🔗"), "Rating": st.column_config.NumberColumn("Rating", format="%.1f ⭐")})

    if st.button("New Search"):
        st.session_state.expander_open = True
        st.session_state.results = None
        st.rerun()
