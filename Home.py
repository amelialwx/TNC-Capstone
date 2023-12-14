import streamlit as st
import leafmap.foliumap as leafmap

# Set page configuration
st.set_page_config(layout="wide", page_title="Home", page_icon="👋")

# Page title
st.title("Web App for TNC Agricultural Plastics Visualization")

st.sidebar.caption("""Source code on [GitHub](https://github.com/amelialwx/TNC-Capstone).""")

# Introduction and description markdown
st.markdown("""
This is an interactive web application created using [Streamlit](https://streamlit.io) for The Nature Conservancy (TNC) to visualize agricultural plastics in California.

- **First Page**: Allows users to train a custom random forest model by uploading CSV data to perform classification and visualization.
- **Second Page**: Utilizes a pre-trained model using data from Oxnard, Santa Maria, Mendocino, and Watsonville, with additional feature engineering to perform classification and visualization.
""")

# Leafmap Map Object
m = leafmap.Map(minimap_control=True)
m.add_basemap("OpenTopoMap")

# Displaying the map in Streamlit
m.to_streamlit(height=500)
