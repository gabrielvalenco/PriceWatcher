"""
Streamlit dashboard for PriceWatcher
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime, timedelta

from pricewatcher.database.connection import get_session
from pricewatcher.database.models import Product, PricePoint, Store
from pricewatcher.utils.helpers import format_price

def start_dashboard():
    """Start the Streamlit dashboard"""
    import subprocess
    import sys
    
    # Run Streamlit in a subprocess
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        os.path.abspath(__file__),
        "--server.port", os.getenv("DASHBOARD_PORT", "8501"),
        "--server.address", os.getenv("DASHBOARD_HOST", "0.0.0.0")
    ]
    
    subprocess.Popen(cmd)

def main():
    """Main Streamlit app function"""
    st.set_page_config(
        page_title="PriceWatcher Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📉 PriceWatcher Dashboard")
    st.write("Monitor your product prices and track their trends over time.")
    
    # Get session
    session = get_session()
    
    try:
        # Overview metrics
        st.header("Overview")
        
        col1, col2, col3 = st.columns(3)
        
        # Count products
        product_count = session.query(Product).filter(Product.active == True).count()
        col1.metric("Products Tracked", product_count)
        
        # Count stores
        store_count = session.query(Store).count()
        col2.metric("Stores", store_count)
        
        # Count price points in the last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_price_points = session.query(PricePoint).filter(PricePoint.timestamp >= yesterday).count()
        col3.metric("Price Updates (24h)", recent_price_points)
        
        # Product list
        st.header("Products")
        products = session.query(Product).filter(Product.active == True).all()
        
        if not products:
            st.info("No products being tracked yet. Add products through the API.")
        else:
            # Convert to list of dicts for display
            product_data = []
            for product in products:
                # Get latest price
                latest_price = session.query(PricePoint).filter(
                    PricePoint.product_id == product.id
                ).order_by(PricePoint.timestamp.desc()).first()
                
                # Get store
                store = session.query(Store).filter(Store.id == product.store_id).first()
                
                price_formatted = format_price(latest_price.price, latest_price.currency) if latest_price else "N/A"
                in_stock = latest_price.in_stock if latest_price else False
                
                product_data.append({
                    "ID": product.id,
                    "Name": product.name,
                    "Store": store.name if store else "Unknown",
                    "Price": price_formatted,
                    "In Stock": "✅" if in_stock else "❌",
                    "Last Updated": latest_price.timestamp.strftime("%Y-%m-%d %H:%M") if latest_price else "N/A"
                })
            
            # Show product table
            df = pd.DataFrame(product_data)
            st.dataframe(
                df,
                column_config={
                    "ID": st.column_config.NumberColumn(
                        "ID",
                        help="Product ID",
                        width="small",
                    ),
                    "Name": st.column_config.TextColumn(
                        "Product Name",
                        width="medium",
                    ),
                    "Store": st.column_config.TextColumn(
                        "Store",
                        width="small",
                    ),
                    "Price": st.column_config.TextColumn(
                        "Current Price",
                        width="small",
                    ),
                    "In Stock": st.column_config.TextColumn(
                        "In Stock",
                        width="small",
                    ),
                    "Last Updated": st.column_config.TextColumn(
                        "Last Updated",
                        width="small",
                    ),
                },
                use_container_width=True
            )
            
            # Product detail view
            st.header("Price History")
            selected_product = st.selectbox(
                "Select a product to view its price history",
                options=[p.id for p in products],
                format_func=lambda x: next((p.name for p in products if p.id == x), str(x))
            )
            
            # Get price history for selected product
            if selected_product:
                price_points = session.query(PricePoint).filter(
                    PricePoint.product_id == selected_product
                ).order_by(PricePoint.timestamp.asc()).all()
                
                if price_points:
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
                    
                    # Display chart
                    st.subheader("Price Trend")
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.plot(price_history["Date"], price_history["Price"], marker='o', linewidth=2)
                    ax.set_title(f"Price History for {next((p.name for p in products if p.id == selected_product), '')}")
                    ax.set_xlabel("Date")
                    ax.set_ylabel(f"Price ({price_history['Currency'].iloc[0]})")
                    ax.grid(True)
                    st.pyplot(fig)
                    
                    # Display data table
                    st.subheader("Price Data")
                    st.dataframe(
                        price_history,
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
                else:
                    st.info("No price history available for this product yet.")
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
    finally:
        session.close()
    
    # Footer
    st.markdown("---")
    st.caption("PriceWatcher Dashboard | Refresh data every hour")

if __name__ == "__main__":
    main()
