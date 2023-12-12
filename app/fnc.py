import ee
import pandas as pd
from datetime import datetime as dt, timedelta
import streamlit as st
import os
from functools import reduce
import geopandas as gpd

tooltip_file_uploader = "Only CSV files are accepted."
tooltip_county = "Select a county for classification."
tooltip_numtrees = "Number of decision trees for the model (1 to 100)."
tooltip_date_input = "Date range for county (ideally 15 days)."
tooltip_left_layer = "Select visualization for the left layer."
tooltip_right_layer = "Select visualization for the right layer."

# Cloud mask for Sentinel-2
def maskS2clouds(image):
    qa = image.select('QA60')
    cloudBitMask = 1 << 10
    cirrusBitMask = 1 << 11
    mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))

    return image.updateMask(mask).divide(10000)


def processImageCollection(imageCollection, aoi, startDate, endDate):
    # Define functions for band calculations
    def addNDVI(image):
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        return image.addBands(ndvi)

    def addNDTI(image):
        ndti = image.normalizedDifference(['B11', 'B12']).rename('NDTI')
        return image.addBands(ndti)

    def addPGI(image):
        NIR = image.select('B8')
        R = image.select('B4')
        G = image.select('B3')
        B = image.select('B2')
        pgi = NIR.subtract(R).multiply(100).multiply(R).divide(NIR.add(B).add(G).divide(3).subtract(1)).rename('PGI')
        return image.addBands(pgi)

    def addPMLI(image):
        SWIR1 = image.select('B11')
        R = image.select('B4')
        pmli = SWIR1.subtract(R).divide(SWIR1.add(R)).rename('PMLI')
        return image.addBands(pmli)

    def addRPGI(image):
        NIR = image.select('B8')
        R = image.select('B4')
        G = image.select('B3')
        B = image.select('B2')
        rpgi = B.multiply(100).divide(NIR.add(B).add(G).divide(3).subtract(1)).rename('RPGI')
        return image.addBands(rpgi)

    # Apply functions to image collection
    processedCollection = (imageCollection
                           .filterDate(startDate, endDate)
                           .filterBounds(aoi)
                           .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                           .map(maskS2clouds)
                           .map(addNDVI)
                           .map(addNDTI)
                           .map(addPGI)
                           .map(addPMLI)
                           .map(addRPGI))

    return processedCollection
    

def get_collection_on_date(df, county, date, roi, bands):
    # Filter for date
    df_date = df[df["Date"]==date]

    # Get coordinates as a list
    points = []
    for idx, row in df_date.iterrows():
        point = ee.Geometry.Point([row['Longitude'], row['Latitude']])
        feature = ee.Feature(point, {'class': row['NumericType']})
        points.append(feature)

    fc = ee.FeatureCollection(points)

    # Get image for a month's range
    date_ = dt.strptime(date, "%Y-%m-%d")
    start = (date_ - timedelta(days=15)).strftime("%Y-%m-%d")
    end = (date_ + timedelta(days=15)).strftime("%Y-%m-%d")
    processedCollection = processImageCollection(ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED'), roi, start, end)
    image = processedCollection.median().clip(roi)

    # Sample points from image
    data = image.select(bands).sampleRegions(
        collection=fc,
        properties=['class'],
        scale=30,
        geometries=True
    )

    print(f"Total number of labeled data for {date} in {county}:", data.size().getInfo())

    return data


def get_data_as_points(df):
    points = []
    for idx, row in df.iterrows():
        point = ee.Geometry.Point([row['Longitude'], row['Latitude']])
        feature = ee.Feature(point, {'class': row['NumericType']})
        points.append(feature)

    return points


def processData(df, county, class_mapping, bands):
    # Encode labels
    df['NumericType'] = df['Type'].map(class_mapping)

    # Drop green house type (for now)
    df = df[df["Type"]!="green house"]

    # Format dates to YYYY-MM-DD
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

    # Filter for dates when Sentinel-2 is available
    df = df[df['Date'] > '2018-05-09'] 

    # County boundaries based off csv coordinates
    min_lon = df['Longitude'].min()
    max_lon = df['Longitude'].max()
    min_lat = df['Latitude'].min()
    max_lat = df['Latitude'].max()

    roi = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])

    # Iterate through unique dates
    dates = df["Date"].unique()
    all_county_data = []
    for date in dates:
        all_county_data.append(get_collection_on_date(df, county, date, roi, bands))
    county_fc = ee.FeatureCollection(all_county_data).flatten()
    print(f"Total number of labeled data in {county}:", county_fc.size().getInfo())

    return county_fc


def get_centroid_coordinates(county_name, counties):
    # Filter the FeatureCollection to the selected county
    selected_county = counties.filter(ee.Filter.eq('NAME', county_name))

    # Calculate the centroid
    centroid = selected_county.geometry().centroid().getInfo()['coordinates']

    return centroid


# def color_point(feature):
#     # Map csv points to corresponding color
#     color = mapping.get(feature.get('Type'))
#     return feature.set('color', color)


def load_data_df(uploaded_files, class_mapping, bands):
    dfs = []
    for file in uploaded_files:
        df = pd.read_csv(file)
        dfs.append(df)

    images = []
    if dfs:
        for df, filename in zip(dfs, [file.name for file in uploaded_files]):
            image = processData(df, filename, class_mapping, bands)
            images.append(image)

    return dfs, images


def train_rf(numtrees, data, bands):
    model = ee.Classifier.smileRandomForest(numtrees)
    return model.train(data, 'class', bands)


def check_data_exists(data_path, csv_filenames, shape_filenames):
    # Check that data folder exists
    if not os.path.exists(data_path):
        st.error(f"Folder does not exist {data_path}")
        return False
    
    # Check that the csv files exist
    for filename in csv_filenames:
        filepath = os.path.join(data_path, filename) + '.csv'
        if not os.path.exists(filepath):
            st.error(f"CSV file does not exist: {filepath}")
            return False
    
    # Check each shapefile component
    shape_ext = ['cpg', 'dbf', 'fix', 'prj', 'shp', 'shx']
    for group in shape_filenames:
        for filename in group:
            for ext in shape_ext:
                filepath = os.path.join(data_path, f'{filename}.{ext}')
                if not os.path.exists(filepath):
                    st.error(f"Shapefile component does not exist: {filepath}")
    return True


def load_data(data_path, csv_filenames, shape_filenames):
    # Load in csv files
    csv_data = []
    for filename in csv_filenames:
        try:
            df = pd.read_csv(os.path.join(data_path, filename) + '.csv')
            csv_data.append(df)
        except Exception as e:
            st.error(f"Failed to load CSV file '{filename}': {e}")
    
    # Load in shape files
    shape_data = []
    for group in shape_filenames:
        group_data = []
        for filename in group:
            try:
                shapefile_gpd = gpd.read_file(os.path.join(data_path, f'{filename}.shp'))
                shapefile_geojson = shapefile_gpd.__geo_interface__
                shapefile = ee.FeatureCollection(shapefile_geojson['features'])
                group_data.append(shapefile)
            except Exception as e:
                st.error(f"Failed to load shape file '{filename}.shp': {e}")
        shape_data.append(group_data)
    
    return csv_data, shape_data


def merge_polygons(poly1, poly2):
    return poly1.merge(poly2)


def create_fc_csv(csv_data, csv_filenames, class_mapping, bands):
    fcs = []
    for data, filename in zip(csv_data, csv_filenames):
        fc = processData(data, filename, class_mapping, bands)
        fcs.append(fc)
    return fcs


def create_fc_shape(shape_data, dates):
    fcs = []
    for i, group in enumerate(shape_data):
        # Merge polygons
        polygons = reduce(merge_polygons, group[1:])
        # Create processed collection
        START = dates[i][0]
        END = dates[i][1]
        processedCollection = processImageCollection(ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED'), group[0], START, END)
        image = processedCollection.median().clip(group[0])
        fc = image.sampleRegions(
            collection=polygons,
            properties=['class'],
            scale=30,
            geometries=True
        )
        fcs.append(fc)
    return fcs