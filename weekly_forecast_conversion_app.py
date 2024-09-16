import streamlit as st
import pandas as pd
import numpy as np
from pandas.tseries.offsets import BDay

# Function to convert monthly forecast to weekly forecast for a single group
def convert_monthly_to_weekly_forecast(monthly_forecast_df, earliest_year):
    daily_forecast = {}
    
    # Initialize the month number
    month_start_date = pd.Timestamp(f'{earliest_year}-01-27')
    month_number_map = {}
    current_month_number = 1
    
    # Create a mapping from month to month number
    for _, row in monthly_forecast_df.iterrows():
        month = row['Month']
        month_start = pd.to_datetime(f"{month}-27") - pd.DateOffset(months=1)
        month_end = pd.to_datetime(f"{month}-26")
        
        if month_start not in month_number_map:
            month_number_map[month_start] = current_month_number
            current_month_number += 1
    
    daily_forecast_list = []
    
    for _, row in monthly_forecast_df.iterrows():
        month = row['Month']
        forecast = row['Monthly Forecast']
        
        start_date = pd.to_datetime(f"{month}-27") - pd.DateOffset(months=1)
        end_date = pd.to_datetime(f"{month}-26")
        
        # Calculate only weekdays in the range
        workdays = pd.date_range(start=start_date, end=end_date, freq='B')
        daily_value = forecast / len(workdays)
        
        # Distribute the forecast over weekdays only
        for date in workdays:
            daily_forecast_list.append({
                'Date': date,
                'Daily Forecast': daily_value,
                'Month Number': month_number_map[start_date]
            })
    
    # Convert daily_forecast list to DataFrame
    daily_forecast_df = pd.DataFrame(daily_forecast_list)
    
    # Format the Date column to display only the date
    daily_forecast_df['Date'] = daily_forecast_df['Date'].dt.strftime('%Y-%m-%d')
    
    # Add a column for the day of the week
    daily_forecast_df['Day of Week'] = pd.to_datetime(daily_forecast_df['Date']).dt.day_name()
    
    # Aggregate into Weekly Data (starting from 27th Dec of previous year)
    start_week = pd.Timestamp(f'{earliest_year-1}-12-27') + pd.offsets.Week(weekday=0)
    daily_forecast_df['Week'] = (pd.to_datetime(daily_forecast_df['Date']) - start_week).dt.days // 7 + 1
    
    # Aggregate daily forecast to weekly forecast
    weekly_forecast = daily_forecast_df.groupby(['Month Number', 'Week']).agg({'Daily Forecast': 'sum'}).reset_index()
    
    # Calculate total forecast for each month
    monthly_totals = daily_forecast_df.groupby('Month Number')['Daily Forecast'].sum().reset_index()
    monthly_totals = monthly_totals.rename(columns={'Daily Forecast': 'Monthly Total Forecast'})
    
    # Merge monthly totals with weekly forecast
    weekly_forecast = pd.merge(weekly_forecast, monthly_totals, on='Month Number')
    
    # Calculate Percentage Contribution
    weekly_forecast['PercentageContribution'] = (weekly_forecast['Daily Forecast'] / weekly_forecast['Monthly Total Forecast']) * 100
    
    # Add the Week Number as a separate column in the weekly DataFrame
    weekly_forecast['Week Number'] = weekly_forecast['Week']
    
    return weekly_forecast, daily_forecast_df

# Streamlit app code
st.title('Monthly to Weekly Forecast Converter')

# File uploader
uploaded_file = st.file_uploader("Upload Monthly Forecast Excel File", type=["xlsx"])

if uploaded_file is not None:
    # Read the uploaded file into a DataFrame
    df = pd.read_excel(uploaded_file)
    df = df.fillna(0)
    
    # Unpivot the DataFrame
    unpivoted_df = pd.melt(df, id_vars=['Country', 'Region', 'Material'], 
                           var_name='Month', value_name='Monthly Forecast')
    
    # Convert 'Month' column to datetime format
    unpivoted_df['Month'] = pd.to_datetime(unpivoted_df['Month'], format='%d/%m/%Y').dt.to_period('M').astype(str)
    
    unpivoted_df['Year'] = unpivoted_df['Month'].str[:4].astype(int)

    # Get the minimum year
    min_year = unpivoted_df['Year'].min()
    
    # Group by Country, Region, and Material
    grouped = unpivoted_df.groupby(['Country', 'Region', 'Material'])
    
    all_weekly_forecast = []
    all_daily_forecast = []

    # Process each group
    for (country, region, material), group_df in grouped:
        weekly_forecast_df, daily_forecast_df = convert_monthly_to_weekly_forecast(group_df, min_year)
        
        weekly_forecast_df['Country'] = country
        weekly_forecast_df['Region'] = region
        weekly_forecast_df['Material'] = material
        
        daily_forecast_df['Country'] = country
        daily_forecast_df['Region'] = region
        daily_forecast_df['Material'] = material
        
        all_weekly_forecast.append(weekly_forecast_df)
        all_daily_forecast.append(daily_forecast_df)
    
    final_weekly_forecast_df = pd.concat(all_weekly_forecast, ignore_index=True)
    final_daily_forecast_df = pd.concat(all_daily_forecast, ignore_index=True)
    
    # Display the weekly forecast table
    st.subheader('Weekly Forecast - Long Format (Unpivoted)')
    final_weekly_forecast_df = final_weekly_forecast_df[['Country', 'Region', 'Material', 'Month Number', 'Week Number', 'Daily Forecast', 'PercentageContribution']]
    final_weekly_forecast_df = final_weekly_forecast_df.rename(columns={'Daily Forecast': 'Weekly Forecast'})
    final_weekly_forecast_df['PercentageContribution'] = final_weekly_forecast_df['PercentageContribution'].round(2).apply(lambda x: '{:.2f}'.format(x).rstrip('0').rstrip('.'))
    base_pivot_df = final_weekly_forecast_df[['Country', 'Region', 'Material', 'Month Number', 'Week Number', 'Weekly Forecast', 'PercentageContribution']]
    final_weekly_forecast_df['Weekly Forecast'] = final_weekly_forecast_df['Weekly Forecast'].round(1).apply(lambda x: '{:.1f}'.format(x).rstrip('0').rstrip('.'))

    st.dataframe(final_weekly_forecast_df.style.hide(axis="index"))
    
    # Pivot and display the weekly forecast table
    st.subheader('Weekly Forecast - Wide Format (Pivoted)')
    base_pivot_df['Weekly Forecast'] = base_pivot_df['Weekly Forecast'].round(1)
    # Strip the trailing zeros using a vectorized function
    strip_zeros = np.vectorize(lambda x: '{:.1f}'.format(x).rstrip('0').rstrip('.') if pd.notnull(x) else x)

    pivot_df = base_pivot_df.pivot_table(
    index=['Country', 'Region', 'Material'], 
    columns=['Month Number', 'Week Number', 'PercentageContribution'], 
    values='Weekly Forecast'
    )
    
    # Apply the stripping function to remove trailing zeros
    pivot_df = pivot_df.apply(strip_zeros)
  
    st.dataframe(pivot_df.style.hide(axis="index"))
    
    # Display the weekly forecast table
    st.subheader('Daily Forecast')
    final_daily_forecast_df = final_daily_forecast_df[['Country', 'Region', 'Material', 'Date', 'Day of Week', 'Week', 'Month Number', 'Daily Forecast']]
    final_daily_forecast_df['Daily Forecast'] = final_daily_forecast_df['Daily Forecast'].round(1).apply(lambda x: '{:.1f}'.format(x).rstrip('0').rstrip('.'))

    st.dataframe(final_daily_forecast_df.style.hide(axis="index"))
    
    
    
    # Weekly Salience
    # File uploader for updated weekly forecast (CSV format)
    st.subheader('Upload Updated Weekly Forecast Percentage for Weekly Salience')
    updated_file = st.file_uploader("Upload the updated Weekly Forecast CSV File", type=["csv"], key="updated_forecast")
    
    # Steps to guide the user
    st.markdown("""
    **Steps:**
    - Download the Weekly Forecast in Long Format (Unpivoted).
    - Update the Percentage Contribution for each week to the respective month as required.
    - Upload the updated Weekly Forecast file with the new percentage contributions.
    """)

    if updated_file is not None:
        # Read the updated file into a DataFrame
        updated_df = pd.read_csv(updated_file)
        
        # Check if the uploaded file contains the necessary columns
        required_columns = ['Country', 'Region', 'Material', 'Month Number', 'Week Number', 'PercentageContribution']
        if all(col in updated_df.columns for col in required_columns):
            # Calculate the Monthly Total Forecast from the weekly forecasts
            monthly_totals = updated_df.groupby(['Country', 'Region', 'Material', 'Month Number'])['Weekly Forecast'].sum().reset_index()
            monthly_totals = monthly_totals.rename(columns={'Weekly Forecast': 'Monthly Total Forecast'})
            
            # Merge the monthly totals with the updated DataFrame
            updated_df = pd.merge(updated_df, monthly_totals, on=['Country', 'Region', 'Material', 'Month Number'])
            
            # Calculate the new Weekly Forecast based on updated PercentageContribution
            updated_df['Weekly Forecast'] = (updated_df['PercentageContribution'] / 100) * updated_df['Monthly Total Forecast']
            
            st.write("Updated Weekly Forecast Based on Percentage Contributions - Long Format (Unpivoted):")
            updated_df['PercentageContribution'] = updated_df['PercentageContribution'].round(2).apply(lambda x: '{:.2f}'.format(x).rstrip('0').rstrip('.'))
            base_pivot_df_updated = updated_df[['Country', 'Region', 'Material', 'Month Number', 'Week Number', 'Weekly Forecast', 'PercentageContribution']]
            
            updated_df['Weekly Forecast'] = updated_df['Weekly Forecast'].round(1).apply(lambda x: '{:.1f}'.format(x).rstrip('0').rstrip('.'))
        
            st.dataframe(updated_df[['Country', 'Region', 'Material', 'Month Number', 'Week Number', 'Weekly Forecast', 'PercentageContribution']].style.hide(axis="index"))
            
            # Pivot and display the weekly forecast table
            st.write("Updated Weekly Forecast Based on Percentage Contributions - Wide Format (Pivoted)")
            base_pivot_df_updated['Weekly Forecast'] = base_pivot_df_updated['Weekly Forecast'].round(1)
            # Strip the trailing zeros using a vectorized function
            strip_zeros = np.vectorize(lambda x: '{:.1f}'.format(x).rstrip('0').rstrip('.') if pd.notnull(x) else x)

            pivot_df_updated = base_pivot_df_updated.pivot_table(
            index=['Country', 'Region', 'Material'], 
            columns=['Month Number', 'Week Number', 'PercentageContribution'], 
            values='Weekly Forecast'
            )

            # Apply the stripping function to remove trailing zeros
            pivot_df_updated = pivot_df_updated.apply(strip_zeros)

            st.dataframe(pivot_df_updated.style.hide(axis="index"))
             
        else:
            st.error("The uploaded file is missing one or more required columns.")
else:
    st.warning("Please upload an Excel file to proceed.")
