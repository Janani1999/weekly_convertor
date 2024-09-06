import streamlit as st
import pandas as pd
from pandas.tseries.offsets import BDay

# Function to convert monthly forecast to weekly forecast for a single group
def convert_monthly_to_weekly_forecast(monthly_forecast_df, earliest_year):
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
            daily_forecast[date] = daily_forecast.get(date, 0) + daily_value
            
    # Convert daily_forecast dictionary to DataFrame
    daily_forecast_df = pd.DataFrame(list(daily_forecast.items()), columns=['Date', 'Daily Forecast'])
    
    # Format the Date column to display only the date
    daily_forecast_df['Date'] = daily_forecast_df['Date'].dt.strftime('%Y-%m-%d')
    
    # Add a column for the day of the week
    daily_forecast_df['Day of Week'] = daily_forecast_df['Date'].apply(pd.to_datetime).dt.day_name()

    # Step 2: Aggregate into Weekly Data (starting from 27th Dec of previous month)
    start_week = pd.Timestamp(f'{earliest_year-1}-12-27') + pd.offsets.Week(weekday=0)  # Dec 27 of the year before the earliest year
    
    # Set the first Monday of the year as the starting week
    daily_forecast_df['Week'] = (pd.to_datetime(daily_forecast_df['Date']) - start_week).dt.days // 7 + 1
    
    # Aggregate daily forecast to weekly forecast
    weekly_forecast = daily_forecast_df.groupby('Week').agg({'Daily Forecast': 'sum'}).reset_index()

    # Add the Week number as a separate column in the weekly DataFrame
    weekly_forecast['Week Number'] = weekly_forecast['Week']

    return weekly_forecast, daily_forecast_df

# Streamlit app code
st.title('Monthly to Weekly Forecast Converter')

# File uploader
uploaded_file = st.file_uploader("Upload Monthly Forecast Excel File", type=["xlsx"])

if uploaded_file is not None:
    # Read the uploaded file into a DataFrame
    df = pd.read_excel(uploaded_file)
    
    # Unpivot the DataFrame
    unpivoted_df = pd.melt(df, id_vars=['Country', 'Region', 'Material'], 
                           var_name='Month', value_name='Monthly Forecast')
    
    # Convert 'Month' column to datetime format
    unpivoted_df['Month'] = pd.to_datetime(unpivoted_df['Month'], format='%d/%m/%Y').dt.to_period('M').astype(str)
    
    unpivoted_df2 = unpivoted_df
    unpivoted_df2['Year'] = unpivoted_df2['Month'].str[:4].astype(int)

    # Get the minimum year
    min_year = unpivoted_df['Year'].min()
    
    # Group by Country, Region, and Material
    grouped = unpivoted_df.groupby(['Country', 'Region', 'Material'])
    
    all_weekly_forecast = []
    all_daily_forecast = []

    # Process each group
    for (country, region, material), group_df in grouped:
        weekly_forecast_df, daily_forecast_df = convert_monthly_to_weekly_forecast(group_df,min_year)
        
        # Add country, region, and material columns to the results
        weekly_forecast_df['Country'] = country
        weekly_forecast_df['Region'] = region
        weekly_forecast_df['Material'] = material
        
        daily_forecast_df['Country'] = country
        daily_forecast_df['Region'] = region
        daily_forecast_df['Material'] = material
        
        # Append results to the list
        all_weekly_forecast.append(weekly_forecast_df)
        all_daily_forecast.append(daily_forecast_df)
    
    # Concatenate all results into single DataFrames
    final_weekly_forecast_df = pd.concat(all_weekly_forecast, ignore_index=True)
    final_daily_forecast_df = pd.concat(all_daily_forecast, ignore_index=True)
    
    # Display the weekly forecast DataFrame
    st.subheader('Weekly Forecast')
    final_weekly_forecast_df = final_weekly_forecast_df[['Country', 'Region', 'Material', 'Week Number', 'Daily Forecast']]
    final_weekly_forecast_df = final_weekly_forecast_df.rename(columns={'Daily Forecast': 'Weekly Forecast'})
    final_weekly_forecast_df['Weekly Forecast'] = final_weekly_forecast_df['Weekly Forecast'].round(1).apply(lambda x: '{:.1f}'.format(x).rstrip('0').rstrip('.'))

    st.dataframe(final_weekly_forecast_df.style.hide(axis="index"))
    
    # Optionally, display the daily forecast DataFrame
    st.subheader('Daily Forecast')
    final_daily_forecast_df = final_daily_forecast_df[['Country', 'Region', 'Material', 'Date', 'Day of Week', 'Week', 'Daily Forecast']]
    final_daily_forecast_df['Daily Forecast'] = final_daily_forecast_df['Daily Forecast'].round(1).apply(lambda x: '{:.1f}'.format(x).rstrip('0').rstrip('.'))

    st.dataframe(final_daily_forecast_df.style.hide(axis="index"))
else:
    st.warning("Please upload an Excel file to proceed.")
