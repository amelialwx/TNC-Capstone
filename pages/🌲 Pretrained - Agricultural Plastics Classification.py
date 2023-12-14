import datetime
import ee
import streamlit as st
import geemap.foliumap as geemap
from datetime import datetime as dt, timedelta
from functools import reduce
import json
import app.fnc as fnc


# Page configuration
st.set_page_config(layout="wide", page_title="Web App")
st.title("Pretrained Model - Agricultural Plastics Classification")

st.sidebar.caption("""Source code on [GitHub](https://github.com/amelialwx/TNC-Capstone).""")

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
    # Additional Geographical Features
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
if 'model_2' not in st.session_state:
    st.session_state.model_2 = None
if 'csv_data_2' not in st.session_state:
    st.session_state.csv_data_2 = None
if 'shape_data_2' not in st.session_state:
    st.session_state.shape_data_2 = None
if 'fcs_shape_2' not in st.session_state:
    st.session_state.fcs_shape_2 = None
if 'county_2' not in st.session_state:
    st.session_state.county_2 = None
if 'start_date_2' not in st.session_state:
    st.session_state.start_date_2 = None
    st.session_state.end_date_2 = None
if 'image_2' not in st.session_state:
    st.session_state.image_2 = None
if 'classified_RF_2' not in st.session_state:
    st.session_state.classified_RF_2 = None
if 'layers_2' not in st.session_state:
    st.session_state.layers_2 = None
        

# ======= SET DATA PATHS =======   
data_path = "data"
csv_filenames = ['Mendocino', 'SantaMaria', 'Watsonville']
shape_filenames = [['Oxnard', 'label_mulch_hoop', 'label_nonplastic']]
dates = [['2019-02-01', '2019-06-01']]
# ==============================

with st.container():
    if st.session_state.model_2 == None:
        bar = st.progress(0, text="Checking if data files exist...")
        # Check if data exists
        success = fnc.check_data_exists(data_path, csv_filenames, shape_filenames)
        if success:
            bar.progress(25, text="Data exists! Loading in data...")
            # Load in the data
            st.session_state.csv_data_2, st.session_state.shape_data_2 = fnc.load_data(data_path, csv_filenames, shape_filenames)
            bar.progress(50, text="Data loaded! Creating feature collection...")
            # Create data
            fcs_csv = fnc.create_fc_csv(st.session_state.csv_data_2, csv_filenames, class_mapping, bands)
            st.session_state.fcs_shape_2 = fnc.create_fc_shape(st.session_state.shape_data_2, dates)
            all_fcs = fcs_csv + st.session_state.fcs_shape_2
            bar.progress(75, text='Feature collection created! Training the model...')
            # Train the model
            data = ee.FeatureCollection(all_fcs).flatten().randomColumn(seed=0)
            st.session_state.model_2 = ee.Classifier.smileRandomForest(50).train(data, 'class', bands)
            bar.progress(100, text='Model trained!')
    else:
        bar = st.progress(100, text="Using existing trained model.")

# Set column layout
col1, col2 = st.columns([4, 1])

with col2:
    print("===============RELOAD===============")

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

    with st.spinner('Loading...'):
        # Create ground truth layers (labeled CSV points for visualization)
        layers = {}
        if st.session_state.layers_2 == None:
            print("Creating gound truth layers...")
            # Define a dictionary of style properties per class type
            class_styles = ee.Dictionary({
                '0': {'color': '1e90ff', 'width': 1, 'fillColor': 'red', 'pointSize': 5, 'pointShape': 'circle'},    # hoop
                '1': {'color': '1e90ff', 'width': 1, 'fillColor': 'green', 'pointSize': 5, 'pointShape': 'circle'},  # mulch
                '2': {'color': '1e90ff', 'width': 1, 'fillColor': 'blue', 'pointSize': 5, 'pointShape': 'circle'},  # other
                '3': {'color': '1e90ff', 'width': 1, 'fillColor': 'yellow', 'pointSize': 5, 'pointShape': 'circle'}   # green house
            })

            # Create ground truth layer(s) for CSV data
            for df, filename in zip(st.session_state.csv_data_2, csv_filenames):
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

            # Create ground truth layer(s) for shape data
            for fc_shape, filename in zip(st.session_state.fcs_shape_2, [group[0] for group in shape_filenames]):
                # Map a function over the FeatureCollection to set the style property
                fc_shape = fc_shape.map(
                    lambda feature: feature.set(
                        'style',
                        class_styles.get(
                            ee.Number(feature.get('class')).format()  # Convert the class number to string to use as key
                        )
                    )
                )

                # Style the FeatureCollection according to each feature's 'style' property.
                style_points_layer = fc_shape.style(
                    styleProperty='style',
                    neighborhood=8
                )

                layers[filename] = geemap.ee_tile_layer(style_points_layer, {}, filename)
            st.session_state.layers_2 = layers
        else:
            print("Ground truth layers already created.")
        
        # County to classify on
        county = 'Los Angeles'
        if option:
            county = option
        # Check if the county or date range has changed
        if (county != st.session_state.county_2) or (st.session_state.start_date_2 != start_date) or (st.session_state.end_date_2 != end_date):
            selected_county = counties.filter(ee.Filter.eq('NAME', county))
            roi = selected_county.geometry()
            processedCollection = fnc.processImageCollection(ee.ImageCollection('COPERNICUS/S2_SR'), roi, start_date, end_date)
            image = processedCollection.median().clip(roi)
            print(f'COUNTY: Classifying on {county}.')

            # Classify
            classified_RF = image.select(bands).classify(st.session_state.model_2)
            accuracy_RF = st.session_state.model_2.confusionMatrix()
            print(f"RESULTS: RF Resubstitution error matrix: {accuracy_RF.getInfo()}")
            print(f"RESULTS: RF Training overall accuracy: {accuracy_RF.accuracy().getInfo()}")

            # Update the session state with the current values
            st.session_state.county_2 = county
            st.session_state.start_date_2 = start_date
            st.session_state.end_date_2 = end_date
            st.session_state.image_2 = image
            st.session_state.classified_RF_2 = classified_RF
        else:
            print(f'No change in county or date range. Using previous image for: {st.session_state.county_2}')

        palette = ['red', 'green', 'blue', 'yellow']

        # Map slider
        st.session_state.layers_2["Sentinel-2 RGB"] = geemap.ee_tile_layer(st.session_state.image_2.select(bands), {'min': 0, 'max': 0.3, 'gamma': 1.4}, "Sentinel-2 RGB")
        st.session_state.layers_2["Classification"] = geemap.ee_tile_layer(st.session_state.classified_RF_2, {'min': 0, 'max': 3, 'palette': palette}, "Classification")

        options = list(st.session_state.layers_2.keys())
        left = st.selectbox("Select a left layer:", options, index=len(options) - 2, help=fnc.tooltip_left_layer)
        right = st.selectbox("Select a right layer:", options, index=len(options) - 1, help=fnc.tooltip_right_layer)
        left_layer = st.session_state.layers_2[left]
        right_layer = st.session_state.layers_2[right]
        Map.split_map(left_layer, right_layer)
        
        # Add legend
        legend_titles = ['Hoop', 'Mulch', 'Other', 'Green House']
        Map.add_legend(title="Classification Legend", legend_dict=dict(zip(legend_titles, palette)))

with col1:
    # Display map
    Map.to_streamlit(height=750)

    # Display CSV dataframes
    tabs = st.tabs(csv_filenames)
    for df, tab, filename in zip(st.session_state.csv_data_2, tabs, csv_filenames):
        with tab:
            st.write(f"Contents of the file {filename}.csv:")
            st.dataframe(df)
