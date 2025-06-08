import streamlit as st
import pandas as pd
import snowflake.connector
import pydeck as pdk
import plotly.express as px

# Streamlit UI Configuration
st.set_page_config(page_title="US POI Map", layout="wide")
st.title("📍 US POI Map Viewer")
st.markdown("View Points of Interest from Snowflake with Map, Filters, and Visualizations")

# Get Snowflake connection
@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        user=st.secrets["user"],
        password=st.secrets["password"],
        account=st.secrets["account"],
        warehouse=st.secrets["warehouse"],
        database=st.secrets["database"],
        schema=st.secrets["schema"]
    )

# Attempt to connect
try:
    conn = get_connection()
except Exception as e:
    st.error("❌ Failed to connect to Snowflake. Please check your credentials.")
    st.stop()

# Fetch data
query = "SELECT * FROM POI_ADDRESS_US"
df = pd.read_sql(query, conn)
conn.close()

# Clean and validate data
df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")
df = df.dropna(subset=["LATITUDE", "LONGITUDE"])

# Sidebar filters
st.sidebar.header("🔍 Filter Options")
category_options = sorted(df["CATEGORY_MAIN"].dropna().unique())
if not category_options:
    st.warning("No categories found in the data.")
    st.stop()

category = st.sidebar.selectbox("Select Category", category_options)
filtered_df = df[df["CATEGORY_MAIN"] == category]

state_options = ["All"] + sorted(filtered_df["STATE"].dropna().unique())
state = st.sidebar.selectbox("Select State", state_options)
if state != "All":
    filtered_df = filtered_df[filtered_df["STATE"] == state]

city_options = ["All"] + sorted(filtered_df["CITY"].dropna().unique())
city = st.sidebar.selectbox("Select City", city_options)
if city != "All":
    filtered_df = filtered_df[filtered_df["CITY"] == city]

row_count = st.sidebar.slider("Number of rows to display", min_value=1, max_value=len(filtered_df), value=min(10, len(filtered_df)))

# Summary
st.success(f"Total POIs in selection: {len(filtered_df)}")

# Map View
st.subheader("🗺️ Map View")
if not filtered_df.empty:
    st.pydeck_chart(pdk.Deck(
        initial_view_state=pdk.ViewState(
            latitude=filtered_df["LATITUDE"].mean(),
            longitude=filtered_df["LONGITUDE"].mean(),
            zoom=10,
            pitch=40,
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=filtered_df,
                get_position='[LONGITUDE, LATITUDE]',
                get_color='[0, 128, 255, 160]',
                get_radius=150,
                pickable=True,
            ),
        ],
        tooltip={"text": "{POI_NAME}\n{CATEGORY_MAIN}\n{CITY}, {STATE}"}
    ))
else:
    st.warning("No data available for the selected filters.")

# Data Table
st.subheader("📋 Selected POI Records")
st.dataframe(filtered_df[["POI_NAME", "CATEGORY_MAIN", "CITY", "STATE", "LATITUDE", "LONGITUDE"]].head(row_count))

# Download CSV
st.download_button(
    label="⬇️ Download Filtered Data as CSV",
    data=filtered_df.to_csv(index=False),
    file_name="filtered_poi_data.csv",
    mime="text/csv"
)

# Category Distribution (Bar Chart)
st.subheader("📊 POI Category Distribution (All Data)")
category_counts = df["CATEGORY_MAIN"].value_counts().reset_index()
category_counts.columns = ["Category", "Count"]
st.bar_chart(category_counts.set_index("Category"))

# Category Distribution (Pie Chart)
st.subheader("📈 Category Distribution Pie Chart")
fig = px.pie(category_counts, names="Category", values="Count", title="POIs by Category")
st.plotly_chart(fig)

# State Distribution
st.subheader("🏙️ POI Distribution by State (All Data)")
state_counts = df["STATE"].value_counts().reset_index()
state_counts.columns = ["State", "POI Count"]
st.bar_chart(state_counts.set_index("State"))
