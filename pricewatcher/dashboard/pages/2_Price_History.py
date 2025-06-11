"""
Price History Visualization page for PriceWatcher dashboard
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

from pricewatcher.database.connection import get_session
from pricewatcher.database.models import Product, PricePoint, Store
from pricewatcher.utils.helpers import format_price

st.set_page_config(
    page_title="Price History | PriceWatcher",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Price History Visualization")
st.write("Track price trends and analyze historical data for your products.")

# Get session
session = get_session()

try:
    # Get all active products
    products = session.query(Product).filter(Product.active == True).all()
    
    if not products:
        st.info("No products being tracked yet. Add products through the API.")
    else:
        # Product selection
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_product = st.selectbox(
                "Select a product",
                options=[p.id for p in products],
                format_func=lambda x: next((p.name for p in products if p.id == x), str(x))
            )
        
        with col2:
            # Time range selection
            time_ranges = {
                "1 Week": 7,
                "1 Month": 30,
                "3 Months": 90,
                "6 Months": 180,
                "1 Year": 365,
                "All Time": None
            }
            selected_range = st.selectbox("Time Range", options=list(time_ranges.keys()))
        
        # Get product details
        product = next((p for p in products if p.id == selected_product), None)
        store = session.query(Store).filter(Store.id == product.store_id).first() if product else None
        
        if product and store:
            # Get price history for selected product
            query = session.query(PricePoint).filter(PricePoint.product_id == product.id)
            
            # Apply time range filter
            days = time_ranges[selected_range]
            if days:
                start_date = datetime.utcnow() - timedelta(days=days)
                query = query.filter(PricePoint.timestamp >= start_date)
            
            price_points = query.order_by(PricePoint.timestamp.asc()).all()
            
            if not price_points:
                st.info("No price history available for this product in the selected time range.")
            else:
                # Convert to DataFrame for plotting
                price_history = pd.DataFrame([
                    {
                        "Date": pp.timestamp,
                        "Price": pp.price,
                        "Currency": pp.currency,
                        "In Stock": pp.in_stock
                    }
                    for pp in price_points
                ])
                
                # Calculate price statistics
                min_price = price_history["Price"].min()
                max_price = price_history["Price"].max()
                avg_price = price_history["Price"].mean()
                current_price = price_history["Price"].iloc[-1]
                
                # Display price metrics
                st.header(f"{product.name}")
                st.write(f"Store: {store.name}")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Current Price", f"{format_price(current_price, price_history['Currency'].iloc[-1])}")
                col2.metric("Lowest Price", f"{format_price(min_price, price_history['Currency'].iloc[-1])}")
                col3.metric("Highest Price", f"{format_price(max_price, price_history['Currency'].iloc[-1])}")
                col4.metric("Average Price", f"{format_price(avg_price, price_history['Currency'].iloc[-1])}")
                
                # Display chart
                st.subheader("Price Trend")
                
                # Create figure with two subplots - price and stock status
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
                
                # Price chart
                ax1.plot(price_history["Date"], price_history["Price"], marker='o', linewidth=2, color='#1f77b4')
                ax1.set_title(f"Price History for {product.name}")
                ax1.set_ylabel(f"Price ({price_history['Currency'].iloc[0]})")
                ax1.grid(True)
                
                # Format x-axis dates based on the time range
                if days and days <= 30:
                    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                else:
                    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
                
                # Add horizontal lines for min, max, and average prices
                ax1.axhline(y=min_price, color='g', linestyle='--', alpha=0.7, label=f"Min: {format_price(min_price, price_history['Currency'].iloc[0])}")
                ax1.axhline(y=max_price, color='r', linestyle='--', alpha=0.7, label=f"Max: {format_price(max_price, price_history['Currency'].iloc[0])}")
                ax1.axhline(y=avg_price, color='y', linestyle='--', alpha=0.7, label=f"Avg: {format_price(avg_price, price_history['Currency'].iloc[0])}")
                ax1.legend()
                
                # Stock status chart
                ax2.fill_between(price_history["Date"], 0, 1, where=price_history["In Stock"], color='green', alpha=0.3, label="In Stock")
                ax2.fill_between(price_history["Date"], 0, 1, where=~price_history["In Stock"], color='red', alpha=0.3, label="Out of Stock")
                ax2.set_yticks([0.5])
                ax2.set_yticklabels(["Stock Status"])
                ax2.set_xlabel("Date")
                ax2.legend(loc='upper right')
                
                plt.tight_layout()
                st.pyplot(fig)
                
                # Price change analysis
                st.subheader("Price Change Analysis")
                
                if len(price_history) >= 2:
                    # Calculate price changes
                    first_price = price_history["Price"].iloc[0]
                    last_price = price_history["Price"].iloc[-1]
                    total_change = last_price - first_price
                    percent_change = (total_change / first_price) * 100
                    
                    # Display price change metrics
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric(
                            "Total Price Change", 
                            f"{format_price(total_change, price_history['Currency'].iloc[0])}", 
                            f"{percent_change:.2f}%",
                            delta_color="inverse" if total_change < 0 else "normal"
                        )
                    
                    with col2:
                        # Calculate volatility (standard deviation)
                        volatility = price_history["Price"].std()
                        volatility_percent = (volatility / avg_price) * 100
                        st.metric("Price Volatility", f"{format_price(volatility, price_history['Currency'].iloc[0])}", f"{volatility_percent:.2f}%")
                    
                    # Calculate daily/weekly/monthly average prices
                    if len(price_history) > 7:
                        st.subheader("Average Prices by Period")
                        
                        # Add period columns
                        price_history['Day'] = price_history['Date'].dt.date
                        price_history['Week'] = price_history['Date'].dt.isocalendar().week
                        price_history['Month'] = price_history['Date'].dt.month
                        price_history['Year'] = price_history['Date'].dt.year
                        
                        # Create period identifiers
                        price_history['Week_Year'] = price_history['Year'].astype(str) + '-W' + price_history['Week'].astype(str).str.zfill(2)
                        price_history['Month_Year'] = price_history['Year'].astype(str) + '-' + price_history['Month'].astype(str).str.zfill(2)
                        
                        # Calculate averages
                        daily_avg = price_history.groupby('Day')['Price'].mean().reset_index()
                        weekly_avg = price_history.groupby('Week_Year')['Price'].mean().reset_index()
                        monthly_avg = price_history.groupby('Month_Year')['Price'].mean().reset_index()
                        
                        # Display averages in tabs
                        tab1, tab2, tab3 = st.tabs(["Daily Averages", "Weekly Averages", "Monthly Averages"])
                        
                        with tab1:
                            if len(daily_avg) > 0:
                                st.line_chart(daily_avg.set_index('Day')['Price'])
                            else:
                                st.info("Not enough data for daily averages")
                                
                        with tab2:
                            if len(weekly_avg) > 0:
                                st.line_chart(weekly_avg.set_index('Week_Year')['Price'])
                            else:
                                st.info("Not enough data for weekly averages")
                                
                        with tab3:
                            if len(monthly_avg) > 0:
                                st.line_chart(monthly_avg.set_index('Month_Year')['Price'])
                            else:
                                st.info("Not enough data for monthly averages")
                
                # Display data table
                st.subheader("Price Data")
                st.dataframe(
                    price_history[["Date", "Price", "Currency", "In Stock"]],
                    column_config={
                        "Date": st.column_config.DatetimeColumn(
                            "Date",
                            format="YYYY-MM-DD HH:mm"
                        ),
                        "Price": st.column_config.NumberColumn(
                            "Price",
                            format="%.2f"
                        ),
                        "Currency": None,
                        "In Stock": st.column_config.CheckboxColumn("In Stock")
                    },
                    use_container_width=True
                )
                
                # Download data option
                csv = price_history[["Date", "Price", "Currency", "In Stock"]].to_csv(index=False)
                st.download_button(
                    label="Download Price History Data",
                    data=csv,
                    file_name=f"{product.name}_price_history.csv",
                    mime="text/csv"
                )

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
finally:
    session.close()
