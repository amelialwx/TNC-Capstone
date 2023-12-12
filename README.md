# Web App for Agricultural Plastics Visualization

## Project Team

**The Nature Conservancy**

**Partners**: Darcy Bradley, Kirk R. Klausmeyer

**Mentors**: Chase Van Amburg, Usha Bhalla

**Members**: Amelia Li, Rebecca Qiu, April Chang, Peter Wu, Evan Arnold

## Description

This is a interactive web application for The Nature Conservancy (TNC). This app, built using Streamlit, aims to visualize and classify agricultural plastics, providing insightful data to drive environmental conservation efforts.

This app consists of two main pages, each offering unique functionalities:
1. **First page (🌲 Custom - Agricultural Plastics Classification)**: Allows for the user to train a custom model by uploading CSv data to perform classification and visualization.
2. **Second page (🌲 Pretrained - Agricultural Plastics Classification)**: Utilizes a pre-trained model using data from Oxnard, Santa Maria, Mendocino, and Watsonville with additional feature engineering to perform classification and visualization.


## Project Organization
    ├── app
        ├── fnc.py
    ├── data
        ├── label_mulch_hoop.cpg
        ├── label_mulch_hoop.dbf
        ├── label_mulch_hoop.fix
        ├── label_mulch_hoop.prj
        ├── label_mulch_hoop.shp
        ├── label_mulch_hoop.shx
        ├── label_nonplastic.cpg
        ├── label_nonplastic.dbf
        ├── label_nonplastic.fix
        ├── label_nonplastic.prj
        ├── label_nonplastic.shp
        ├── label_nonplastic.shx
        ├── Oxnard.cpg
        ├── Oxnard.dbf
        ├── Oxnard.fix
        ├── Oxnard.prj
        ├── Oxnard.shp
        ├── Oxnard.shx
        ├── Mendocino.csv
        ├── SantaMaria.csv
        └── Watsonville.csv
    ├── pages
        ├── 🌲 Custom - Agricultural Plastics Classification.py
        ├── 🌲 Pretrained - Agricultural Plastics Classification.py
    ├── .gitignore
    ├── Home.py
    ├── LICENSE
    ├── README.md
    └── requirements.txt

## Installation and Setup

**Prerequisites**
```
python --version
```
If you have python 3.12 or above, the app might not work. You can download Python 3.11.6 [here](https://www.python.org/downloads/release/python-3116/).

**Installation Steps**
1. Clone the repository: 
```
git clone https://github.com/amelialwx/TNC-Web-App.git
```
2. Navigate to the projecto directory:
```
cd TNC-Web-App
```
3. Install dependencies
```
pip install -r requirements.txt
```

**Running the app**
1. Start the server:
```
sh startup.sh
```
2. Follow the GEE authentication process.
3. The app should now be running in your browser.
![home](assets/home.png)

## Usage

**Page 1 (🌲 Custom - Agricultural Plastics Classification)**

Features:
- Allows for single/multiple CSV file uploads to train a custom random forest model
- Select a California county to classify on
- Change the number of trees to use for the random forest model
- Select a target date range for classification
- Visualization with slider for side-by-side comparison of two layers
- Customize left and right layer
- Display the uploaded CSV files as dataframes

![Page 1 Demo](assets/page1_demo.gif)

**Page 2 (🌲 Pretrained - Agricultural Plastics Classification)**

Features:
- Utilizes a pretrained model with additional feature engineering on pre-existing data
- Select a Californa county to classify on
- Select a target date range for classification
- Visualization with slider for side-by-side comparison of two layers
- Customize left and right layer
- Display the CSV data as dataframes

![Page 2 Demo](assets/page2_demo.gif)

Any new data for this page must be placed in the data folder and specified under data paths at line 60.
<img src="assets/page2_paths.png" width="50%" height="50%">

## Acknowledgements

Special thanks to Darcy and Kirk for their expert guidance as project partners, and to our mentors, Chase and Usha, for their invaluable support. Our appreciation also goes to Yuanyuan for her advisory role and to TNC volunteer Brandee, whose data contribution was essential to our project's success.







