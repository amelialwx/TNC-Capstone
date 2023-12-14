import datetime
import ee
import streamlit as st
import geemap.foliumap as geemap
from datetime import datetime as dt, timedelta
import json
import app.fnc as fnc


# Page configuration
st.set_page_config(layout="wide", page_title="Web App")
st.title("Custom Model - Agricultural Plastics Classification")

st.sidebar.caption("""Source code on [GitHub](https://github.com/amelialwx/TNC-Capstone).""")

# Set column layout
col1, col2 = st.columns([5, 2])

# GEE authorization (Streamlit cloud)
data_service_account = st.secrets['data-service-account']
service_account = st.secrets['service_account']
json_object = json.dumps(json.loads(data_service_account, strict=False))
credentials = ee.ServiceAccountCredentials(service_account, key_data=json_object)
ee.Initialize(credentials)

# Initialize GEE map
Map = geemap.Map()
Map.add_basemap("SATELLITE")

# Target bands for images
bands = [
    # Spectrum Features
    'B4', 'B3', 'B2', 'B6', 'B8', 'B11', 'B12',
    # Index Features
    'NDVI', 'NDTI', 'PGI', 'PMLI',
]

# Define class mapping
class_mapping = {'hoop': 0, 'mulch': 1, 'other': 2, 'green house': 3}


# Mapping for CSV
mapping = ee.Dictionary({
            'hoop': 'red',
            'mulch': 'green',
            'other': 'blue',
            'green house': 'yellow'
        })

# Initialize session states
if 'filenames_1' not in st.session_state:
    st.session_state.filenames_1 = None
    st.session_state.dfs_1 = None
    st.session_state.images_1 = None
if 'model_1' not in st.session_state:
    st.session_state.model_1 = None
if 'numtrees_1' not in st.session_state:
    st.session_state.numtrees_1 = 50
if 'county_1' not in st.session_state:
    st.session_state.county_1 = None
if 'start_date_1' not in st.session_state:
    st.session_state.start_date_1 = None
    st.session_state.end_date_1 = None
if 'image_1' not in st.session_state:
    st.session_state.image_1 = None
if 'classified_RF_1' not in st.session_state:
    st.session_state.classified_RF_1 = None
if 'layers_1' not in st.session_state:
    st.session_state.layers_1 = None


with col2:
    print("===============RELOAD===============")
    # File upload prompt
    uploaded_files = st.file_uploader("Upload file(s):", accept_multiple_files=True, help=fnc.tooltip_file_uploader)
    filenames = [file.name for file in uploaded_files]

    # List of CA counties
    counties = ee.FeatureCollection('TIGER/2018/Counties')
    ca_counties = counties.filter(ee.Filter.eq('STATEFP', '06'))
    ca_counties_list = sorted(ca_counties.aggregate_array('NAME').getInfo())

    # Let user pick a CA county
    option = st.selectbox('Select a California county:', ca_counties_list, index=None, placeholder="Los Angeles", help=fnc.tooltip_county)
    if not option:
        selected_county_centroid = fnc.get_centroid_coordinates('Los Angeles', counties)
    else:
        selected_county_centroid = fnc.get_centroid_coordinates(option, counties)

    # Calculate coordinates for selected CA county, default otherwise
    longitude = selected_county_centroid[0]
    latitude = selected_county_centroid[1]
    Map.setCenter(longitude, latitude, 11)

    # If this is the first session or if there is a change in the names of the uploaded files
    if st.session_state.filenames_1 == None or st.session_state.filenames_1 != filenames:
        st.session_state.filenames_1 = filenames
        st.session_state.dfs_1, st.session_state.images_1 = fnc.load_data_df(uploaded_files, class_mapping, bands)
    else:
        print(f"No change in uploaded file names. Using previous data and images for: {st.session_state.filenames_1}")

    # If files have been uploaded and processed
    if uploaded_files: 
        # Merge data
        data = ee.FeatureCollection(st.session_state.images_1).flatten().randomColumn(seed=0)

        # Let the user pick the number of trees for the TF model
        numtrees = st.number_input('Number of trees:', min_value=1, max_value=100, value=st.session_state.numtrees_1, help=fnc.tooltip_numtrees)

        if not st.session_state.model_1:
            # Train RF with 50 trees
            print("MODEL: Training a default model with 50 trees...")
            st.session_state.model_1 = fnc.train_rf(50, data, bands)
        elif numtrees != st.session_state.numtrees_1:
            # Train RF with number of trees picked by the user
            print(f'MODEL: Training a model with {numtrees} trees...')
            st.session_state.numtrees_1 = numtrees
            st.session_state.model_1 = fnc.train_rf(st.session_state.numtrees_1, data, bands)
        else:
            print(f"MODEL: Using previous model with {st.session_state.numtrees_1} trees.")

        # Let user pick a date range
        input_dates = st.date_input("Select date range:", [datetime.date(2020, 1, 1), datetime.date(2020, 1, 15)], help=fnc.tooltip_date_input)

        # Check if only one date (start_date) is provided, 15-day range by default
        if len(input_dates) == 1:
            start_date = input_dates[0]
            end_date = start_date + timedelta(days=14)
        else:
            start_date, end_date = input_dates

        # Format dates to strings
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")
        print(f'DATE: {start_date} to {end_date}')

        layers = {}
        if st.session_state.layers_1 == None:
            print("Creating gound truth layers...")
            # Define a dictionary of style properties per class type
            class_styles = ee.Dictionary({
                '0': {'color': '1e90ff', 'width': 1, 'fillColor': 'red', 'pointSize': 5, 'pointShape': 'circle'},    # hoop
                '1': {'color': '1e90ff', 'width': 1, 'fillColor': 'green', 'pointSize': 5, 'pointShape': 'circle'},  # mulch
                '2': {'color': '1e90ff', 'width': 1, 'fillColor': 'blue', 'pointSize': 5, 'pointShape': 'circle'},  # other
                '3': {'color': '1e90ff', 'width': 1, 'fillColor': 'yellow', 'pointSize': 5, 'pointShape': 'circle'}   # green house
            })

            # Create ground truth layer(s) for CSV data
            for df, filename in zip(st.session_state.dfs_1, filenames):
                points = fnc.get_data_as_points(df)
                points_layer = ee.FeatureCollection(points)

                # Map a function over the FeatureCollection to set the style property
                points_layer = points_layer.map(
                    lambda feature: feature.set(
                        'style',
                        class_styles.get(
                            ee.Number(feature.get('class')).format()  # Convert the class number to string to use as key
                        )
                    )
                )

                # Style the FeatureCollection according to each feature's 'style' property.
                style_points_layer = points_layer.style(
                    styleProperty='style',
                    neighborhood=8
                )

                layers[filename] = geemap.ee_tile_layer(style_points_layer, {}, filename)

            st.session_state.layers_1 = layers
        else:
            print("Ground truth layers already created.")
        
        # County to classify on
        county = 'Los Angeles'
        if option:
            county = option
        # Check if the county or date range has changed
        if (county != st.session_state.county_1) or (st.session_state.start_date_1 != start_date) or (st.session_state.end_date_1 != end_date):
            selected_county = counties.filter(ee.Filter.eq('NAME', county))
            roi = selected_county.geometry()
            processedCollection = fnc.processImageCollection(ee.ImageCollection('COPERNICUS/S2_SR'), roi, start_date, end_date)
            image = processedCollection.median().clip(roi)
            print(f'COUNTY: Classifying on {county}.')

            # Classify
            classified_RF = image.select(bands).classify(st.session_state.model_1)
            accuracy_RF = st.session_state.model_1.confusionMatrix()
            print(f"RESULTS: RF Resubstitution error matrix: {accuracy_RF.getInfo()}")
            print(f"RESULTS: RF Training overall accuracy: {accuracy_RF.accuracy().getInfo()}")

            # Update the session state with the current values
            st.session_state.county_1 = county
            st.session_state.start_date_1 = start_date
            st.session_state.end_date_1 = end_date
            st.session_state.image_1 = image
            st.session_state.classified_RF_1 = classified_RF
        else:
            print(f'No change in county or date range. Using previous image for: {st.session_state.county_1}')

        palette = ['red', 'green', 'blue', 'yellow']

        # Map slider
        st.session_state.layers_1["Sentinel-2 RGB"] = geemap.ee_tile_layer(st.session_state.image_1.select(bands), {'min': 0, 'max': 0.3, 'gamma': 1.4}, "Sentinel-2 RGB")
        st.session_state.layers_1["Classification"] = geemap.ee_tile_layer(st.session_state.classified_RF_1, {'min': 0, 'max': 3, 'palette': palette}, "Classification")

        options = list(st.session_state.layers_1.keys())
        left = st.selectbox("Select a left layer:", options, index=len(options) - 2, help=fnc.tooltip_left_layer)
        right = st.selectbox("Select a right layer:", options, index=len(options) - 1, help=fnc.tooltip_left_layer)
        left_layer = st.session_state.layers_1[left]
        right_layer = st.session_state.layers_1[right]
        Map.split_map(left_layer, right_layer)
        
        # Add legend
        legend_titles = ['Hoop', 'Mulch', 'Other', 'Green House']
        Map.add_legend(title="Classification Legend", legend_dict=dict(zip(legend_titles, palette)))

with col1:
    Map.to_streamlit(height=750)
    if uploaded_files:
        tabs = st.tabs(filenames)
        for df, tab, filename in zip(st.session_state.dfs_1, tabs, [file.name for file in uploaded_files]):
            with tab:
                st.write(f"Contents of the file {filename}:")
                st.dataframe(df)
