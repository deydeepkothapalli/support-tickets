# Import Python Packages
import pandas as pd
import streamlit as st
import numpy as np
import altair as alt
from datetime import datetime, timedelta

# Streamlit App
st.title(":pill: Drug Tablet Process Metrics Dashboard :pill:")
st.write(
    """
    This dashboard allows you to visualize control charts, including Upper Control Limit (UCL), Lower Control Limit (LCL), Upper Specification Limit (USL), and Lower Specification Limit (LSL), as well as calculate Ppk and Cpk from a sample tablet manufacturing dataset. Select a metric, date range, and filters to analyze the data.
    """
)

st.header("Metric Descriptions")

# Define the metrics dictionary with updated descriptions
metrics = {
    "date": "Date and time of measurements, recorded every 10 seconds during the manufacturing process",
    "campaign": "Series of production runs for the same product, part of the 1005 batches dataset",
    "batch": "Specific quantity of drug product from a single manufacturing cycle within the dataset",
    "code": "Identifier for product subcategories or formulations in the study",
    "tbl_speed": "Tablet press speed, a critical process parameter affecting production rate and quality",
    "fom": "Force Output Measurement, related to equipment performance during tablet pressing",
    "main_comp": "Main compression force applied during tablet formation, influencing tablet properties",
    "tbl_fill": "Filling speed or volume of powder/granules in die cavities, affecting tablet weight uniformity",
    "SREL": "Standard Relative Deviation, measuring compression force variability during production",
    "pre_comp": "Pre-compression force applied before main compression, ensuring initial material consolidation",
    "produced": "Total number of tablets successfully manufactured in each batch",
    "waste": "Amount of rejected material or defective tablets generated during production",
    "cyl_main": "Main cylinder pressure or force in the tablet press during compression",
    "cyl_pre": "Pre-compression cylinder pressure, applied before final compression",
    "stiffness": "Mechanical properties of tablets or critical equipment components",
    "ejection": "Process of removing compressed tablets from die cavities, critical for tablet integrity"
}

# Create an expander for metric descriptions
with st.expander("Click to view metric descriptions"):
    for metric, description in metrics.items():
        st.markdown(f"**{metric}**: {description}")

st.divider()

# Cache the data retrieval from CSV
@st.cache_data
def get_manufacturing_data(start_date: str, end_date: str, campaign: int = None, batch: int = None):
    try:
        # Read data from 1.csv with semicolon delimiter
        data = pd.read_csv("1.csv", sep=';')
        # Convert all column names to lowercase
        data.columns = data.columns.str.lower()
        # Debug: Print column names to verify
        #st.write("Columns in the dataset:", list(data.columns))
        # Convert timestamp to datetime
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        
        # Filter by date range
        data = data[(data['timestamp'] >= start_date) & (data['timestamp'] <= end_date)]
        
        # Apply campaign and batch filters if provided
        if campaign is not None:
            data = data[data['campaign'] == campaign]
        if batch is not None:
            data = data[data['batch'] == batch]
        
        return data
    except FileNotFoundError:
        st.error("The file '1.csv' was not found. Please ensure it is in the same directory as the app.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data from 1.csv: {str(e)}")
        return pd.DataFrame()

# Cache the retrieval of unique values for filters
@st.cache_data
def get_unique_values(column: str):
    try:
        # Read data from 1.csv with semicolon delimiter
        data = pd.read_csv("1.csv", sep=';')
        # Convert all column names to lowercase
        data.columns = data.columns.str.lower()
        # Debug: Print column names to verify
        #st.write(f"Columns in the dataset (get_unique_values for {column}):", list(data.columns))
        # Check if the column exists
        if column.lower() not in data.columns:
            st.error(f"Column '{column}' not found in the dataset. Available columns: {list(data.columns)}")
            return []
        return sorted(data[column.lower()].unique().tolist())
    except FileNotFoundError:
        st.error("The file '1.csv' was not found. Please ensure it is in the same directory as the app.")
        return []
    except Exception as e:
        st.error(f"Error loading data from 1.csv: {str(e)}")
        return []

# Function to calculate control chart metrics
def calculate_control_chart_metrics(data: pd.DataFrame, metric: str):
    mean = data[metric].mean()
    std = data[metric].std()
    ucl = mean + 3 * std
    lcl = mean - 3 * std
    return mean, ucl, lcl

# Function to calculate Ppk and Cpk
def calculate_process_capability(data: pd.DataFrame, metric: str, lsl: float, usl: float):
    mean = data[metric].mean()
    std = data[metric].std()
    
    # Cpk: Process capability considering both upper and lower specification limits
    cpu = (usl - mean) / (3 * std) if std != 0 else float('inf')
    cpl = (mean - lsl) / (3 * std) if std != 0 else float('inf')
    cpk = min(cpu, cpl)
    
    # Ppk: Process performance (uses the same formula as Cpk but typically for long-term data)
    ppk = cpk  # In this case, we're using the same data for simplicity
    
    return cpk, ppk

# Function to create a control chart using Altair with dynamic x-axis scaling
def create_control_chart(data: pd.DataFrame, metric: str, mean: float, ucl: float, lcl: float, lsl: float, usl: float):
    # Convert timestamps to datetime
    timestamps = pd.to_datetime(data['timestamp'])
    
    # Calculate the time range
    time_range = (timestamps.max() - timestamps.min()).total_seconds()
    
    # Determine the appropriate x-axis format and title based on the time range
    if time_range <= 24 * 60 * 60:  # ≤ 1 day (in seconds)
        x_format = '%H:%M'  # Show time of day (e.g., "02:37")
        x_title = 'Time'
        tick_count = 5  # Show ~5 time labels
    elif time_range <= 30 * 24 * 60 * 60:  # ≤ 1 month (in seconds)
        x_format = '%b %d'  # Show day (e.g., "Nov 23")
        x_title = 'Date'
        tick_count = 7  # Show ~7 day labels
    elif time_range <= 365 * 24 * 60 * 60:  # ≤ 1 year (in seconds)
        x_format = '%b %Y'  # Show month (e.g., "Nov 2018")
        x_title = 'Month'
        tick_count = 6  # Show ~6 month labels
    else:  # > 1 year
        x_format = '%Y'  # Show year (e.g., "2018")
        x_title = 'Year'
        tick_count = 5  # Show ~5 year labels
    
    # Base chart for the metric
    base = alt.Chart(data).encode(
        x=alt.X('timestamp:T',
                title=x_title,
                axis=alt.Axis(format=x_format, labelAngle=45, tickCount=tick_count)),
        y=alt.Y(f'{metric}:Q', title=metric.replace('_', ' ').capitalize()),
        tooltip=['timestamp', metric]
    )
    
    # Plot the metric as points
    points = base.mark_point(color='blue', opacity=0.5).encode(
        color=alt.value('blue'),
        shape=alt.value('circle')
    )
    
    # Create a DataFrame for the lines to enable a legend (no dash patterns)
    lines_data = pd.DataFrame({
        'y': [mean, ucl, lcl, lsl, usl],
        'label': ['Mean', 'UCL (+3σ)', 'LCL (-3σ)', 'LSL', 'USL'],
        'color': ['purple', 'red', 'blue', 'orange', 'green']
    })
    
    # Add lines for Mean, UCL, LCL, LSL, and USL (all solid lines)
    lines = alt.Chart(lines_data).mark_rule().encode(
        y='y:Q',
        color=alt.Color('label:N', scale=alt.Scale(
            domain=['Mean', 'UCL (+3σ)', 'LCL (-3σ)', 'LSL', 'USL'],
            range=['purple', 'red', 'blue', 'orange', 'green']
        ), legend=alt.Legend(title="Lines"))
    )
    
    # Combine all layers
    chart = (points + lines).properties(
        title=f'Control Chart for {metric.replace("_", " ").capitalize()}',
        width=800,
        height=400
    )
    return chart

# UI Elements
# Create columns for date range and metric selection
first_col, second_col = st.columns(2, gap="large")

with first_col:
    start_date, end_date = st.date_input(
        "Select date range for the data:",
        value=(datetime(2018, 11, 22), datetime(2019, 10, 25)),
        min_value=datetime(2018, 11, 22),
        max_value=datetime(2019, 10, 25)
    )

with second_col:
    # Allow selection of all metrics from tbl_speed onwards
    metric = st.selectbox(
        label="Select the metric to analyze:",
        options=['tbl_speed', 'fom', 'main_comp', 'tbl_fill', 'srel', 'pre_comp', 'produced', 'waste', 'cyl_main', 'cyl_pre', 'stiffness', 'ejection'],
        index=0
    )

# Create columns for campaign and batch filters
filter_col1, filter_col2 = st.columns(2, gap="medium")

with filter_col1:
    campaign_options = get_unique_values('campaign')  # Use lowercase 'campaign'
    campaign = st.selectbox(
        label="Filter by Campaign (optional):",
        options=[None] + campaign_options,
        index=0
    )

with filter_col2:
    batch_options = get_unique_values('batch')  # Use lowercase 'batch'
    batch = st.selectbox(
        label="Filter by Batch (optional):",
        options=[None] + batch_options,
        index=0
    )

# Convert dates to string format for filtering
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = end_date.strftime('%Y-%m-%d')

# Fetch data with filters
data = get_manufacturing_data(start_date_str, end_date_str, campaign, batch)

# Ensure data is not empty
if data.empty:
    st.error("No data available for the selected date range and filters.")
else:
    # Convert timestamp to datetime (already done in get_manufacturing_data, but ensure consistency)
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    
    # Calculate control chart metrics
    mean, ucl, lcl = calculate_control_chart_metrics(data, metric)
    
    # Dynamically set the LSL and USL slider range based on the metric's data
    metric_min = float(data[metric].min())
    metric_max = float(data[metric].max())
    # Add some padding to the range for better usability
    padding = (metric_max - metric_min) * 0.1  # 10% padding
    slider_min = metric_min - padding
    slider_max = metric_max + padding
    
    # Set default LSL and USL to mean ± 2 standard deviations
    default_lsl = max(slider_min, mean - 2 * data[metric].std())
    default_usl = min(slider_max, mean + 2 * data[metric].std())
    
    # Calculate Ppk and Cpk
    lsl, usl = st.slider(
        "Set Lower and Upper Specification Limits (LSL, USL):",
        min_value=slider_min,
        max_value=slider_max,
        value=(default_lsl, default_usl),
        step=0.1
    )
    cpk, ppk = calculate_process_capability(data, metric, lsl, usl)
    
    # Create tabs for chart, metrics, and raw data
    chart_tab, metrics_tab, data_tab = st.tabs(["Control Chart", "Process Capability Metrics", "Raw Data"])
    
    with chart_tab:
        chart = create_control_chart(data, metric, mean, ucl, lcl, lsl, usl)
        st.altair_chart(chart, use_container_width=True)
    
    with metrics_tab:
        st.write(f"**Mean ({metric.replace('_', ' ').capitalize()})**: {mean:.2f}")
        st.write(f"**UCL (+3σ)**: {ucl:.2f}")
        st.write(f"**LCL (-3σ)**: {lcl:.2f}")
        st.write(f"**LSL**: {lsl:.2f}")
        st.write(f"**USL**: {usl:.2f}")
        st.write(f"**Cpk**: {cpk:.2f}")
        st.write(f"**Ppk**: {ppk:.2f}")
    
    with data_tab:
        st.dataframe(data, use_container_width=True)
