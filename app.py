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

# --- CSS Injection (Fonts & Colors) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
        
        /* Apply Roboto to absolutely everything */
        html, body, .stApp, [class*="css"], div, span, p, input, button, select {
            font-family: 'Roboto', sans-serif !important;
        }

        /* App container width */
        .main .block-container {
            padding-top: 2rem;
            max-width: 900px;
        }

        /* Match Button to Slider Orange-Red (#FF4B4B) */
        div.stButton > button {
            background-color: #FF4B4B !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            padding: 0.6rem 1rem !important;
            width: 100%;
            transition: 0.3s all ease;
        }
        div.stButton > button:hover {
            background-color: #e64040 !important;
            box-shadow: 0 4px 12px rgba(255, 75, 75, 0.3) !important;
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
        api_key = st.sidebar.text_input("API Key", type="password")

    with st.form("search_form", border=False):
        col1, col2 = st.columns(2)
        with col1:
            loc_a_text = st.text_input("First Location", value="", placeholder="")
            max_mins = st.slider("Max Walking Minutes", 5, 30, 15)
        with col2:
            loc_b_text = st.text_input("Second Location", value="", placeholder="")
            min_rating = st.slider("Minimum Rating", 0, 5, 4)

        CUISINE_OPTIONS = ["Any", "American", "Asian Fusion", "Bakery", "Bar", "Breakfast", "Burgers", "Cafe", "Chinese", "Coffee", "Deli", "Greek", "Indian", "Italian", "Japanese", "Korean", "Mexican", "Middle Eastern", "Pizza", "Salad", "Sandwiches", "Seafood", "Sushi", "Thai", "Vegan", "Vietnamese"]
        selected_cuisines = st.multiselect("Cuisines", options=CUISINE_OPTIONS)
        
        submit_button = st.form_submit_button("Search Locations")

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
                    st.error("Address not found.")
                    st.stop()
                
                coords_a = geo_a[0]['geometry']['location']
                coords_b = geo_b[0]['geometry']['location']
                
                # 2. Search
                search_radius = max_mins * 80 * 1.2
                search_terms = selected_cuisines if (selected_cuisines and "Any" not in selected_cuisines) else [None]
                
                all_venues = []
                for term in search_terms:
                    res = gmaps.places_nearby(location=coords_a, radius=search_radius, type="restaurant", keyword=term)
                    all_venues.extend(res.get('results', []))
                
                # Deduplicate
                venues = list({v['place_id']: v for v in all_venues}.values())
                
                # 3. Distance Matrix
                final_list = []
                if venues:
                    # Limit to top 25 to stay in one DM call for speed
                    venues = venues[:25] 
                    chunk_coords = [v['geometry']['location'] for v in venues]
                    dm = gmaps.distance_matrix(origins=[coords_a, coords_b], destinations=chunk_coords, mode="walking")
                    
                    for j, venue in enumerate(venues):
                        rating = venue.get('rating', 0)
                        if rating < min_rating: continue
                        
                        try:
                            w_a = dm['rows'][0]['elements'][j]['duration']['value'] / 60
                            w_b = dm['rows'][1]['elements'][j]['duration']['value'] / 60
                            
                            if w_a <= max_mins and w_b <= max_mins:
                                maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(venue['name'])}&query_place_id={venue.get('place_id')}"
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
                        except: continue

                if not final_list:
                    st.warning("No matches found within that distance for both people.")
                else:
                    # Save results and flip UI state
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
    
    # Add Start points
    anchors = pd.DataFrame([
        {"lat": res['coords_a']['lat'], "lon": res['coords_a']['lng'], "Name": "Location A", "color_rgb": [0, 100, 255, 255], "tooltip_extra": "Starting Point"},
        {"lat": res['coords_b']['lat'], "lon": res['coords_b']['lng'], "Name": "Location B", "color_rgb": [0, 255, 100, 255], "tooltip_extra": "Starting Point"} 
    ])
    full_df = pd.concat([map_df, anchors], ignore_index=True)

    # Map
    st.pydeck_chart(pdk.Deck(
        map_style='light',
        initial_view_state=pdk.ViewState(
            latitude=full_df['lat'].mean(),
            longitude=full_df['lon'].mean(),
            zoom=13),
        layers=[
            pdk.Layer('ScatterplotLayer', data=full_df, get_position='[lon, lat]', 
                      get_color='color_rgb', get_radius=45, pickable=True),
        ],
        tooltip={"text": "{Name}\n{tooltip_extra}"}
    ))

    # Legend
    st.markdown("""
    <div style="display: flex; gap: 20px; font-size: 13px; margin: 10px 0 30px 0; justify-content: center; color: #666;">
        <div><span style="color:#0064FF">●</span> Start A</div>
        <div><span style="color:#00FF64">●</span> Start B</div>
        <div><span style="color:#FF4B4B">●</span> Matching Restaurants</div>
    </div>
    """, unsafe_allow_html=True)

    # Table
    st.dataframe(
        map_df,
        column_order=["Name", "Rating", "Mins from A", "Mins from B", "Link"],
        use_container_width=True, hide_index=True,
        column_config={
            "Link": st.column_config.LinkColumn("Google Maps", display_text="Directions 🔗"),
            "Rating": st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
        }
    )

    if st.button("Edit Search"):
        st.session_state.expander_open = True
        st.rerun()

elif st.session_state.expander_open:
    st.info("Find the perfect middle ground between two people.")
