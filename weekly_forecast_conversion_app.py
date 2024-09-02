import streamlit as st
import pandas as pd
from pandas.tseries.offsets import BDay

# Function to convert monthly forecast to weekly forecast
def convert_monthly_to_weekly_forecast(monthly_forecast_df):
    daily_forecast = {}
    
    # Step 1: Convert Monthly to Daily Data
    for _, row in monthly_forecast_df.iterrows():
        month = row['Month']
        forecast = row['Monthly Forecast']
        
        # Define start and end dates based on the requirement
        start_date = pd.to_datetime(f"{month}-27") - pd.DateOffset(months=1)
        end_date = pd.to_datetime(f"{month}-26")
        
        # Calculate the number of workdays
        workdays = pd.date_range(start=start_date, end=end_date, freq=BDay())
        daily_value = forecast / len(workdays)
        
        # Distribute the forecast over workdays
        for date in workdays:
            daily_forecast[date] = daily_value
            
    # Convert daily_forecast dictionary to DataFrame
    daily_forecast_df = pd.DataFrame(list(daily_forecast.items()), columns=['Date', 'Daily Forecast'])
    
    # Add a column for the day of the week
    daily_forecast_df['Day of Week'] = daily_forecast_df['Date'].dt.day_name()

    # Step 2: Aggregate into Weekly Data (starting from 27th Dec of previous month)
    start_week = pd.Timestamp('2023-12-27') + pd.offsets.Week(weekday=0)
    
    # Set the first Monday of the year as the starting week
    daily_forecast_df['Week'] = (daily_forecast_df['Date'] - start_week).dt.days // 7 + 1
    
    # Aggregate daily forecast to weekly forecast
    weekly_forecast = daily_forecast_df.groupby('Week').agg({'Daily Forecast': 'sum'}).reset_index()

    # Add the Week number as a separate column in the weekly DataFrame
    #weekly_forecast['Week Number'] = weekly_forecast['Week']

    return weekly_forecast, daily_forecast_df

# Streamlit app code
st.title('Monthly to Weekly Forecast Converter')

# File uploader
uploaded_file = st.file_uploader("Upload Monthly Forecast Excel File", type=["xlsx"])

if uploaded_file is not None:
    # Read the uploaded file into a DataFrame
    monthly_forecast_df = pd.read_excel(uploaded_file)
    
    # Convert the monthly forecast to weekly forecast
    weekly_forecast_df, daily_forecast_df = convert_monthly_to_weekly_forecast(monthly_forecast_df)
    
    # Display the weekly forecast DataFrame
    st.subheader('Weekly Forecast')
    st.dataframe(weekly_forecast_df)
    
    # Optionally, display the daily forecast DataFrame
    st.subheader('Daily Forecast')
    st.dataframe(daily_forecast_df)
else:
    st.warning("Please upload an Excel file to proceed.")
