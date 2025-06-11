"""
Streamlit dashboard for PriceWatcher
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime, timedelta

from pricewatcher.database.connection import get_session
from pricewatcher.database.models import Product, PricePoint, Store, PriceAlert
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
    
    # Sidebar navigation
    with st.sidebar:
        st.title("PriceWatcher")
        st.markdown("### Navigation")
        st.markdown("📊 **Dashboard** (current)")
        st.markdown("🔍 [Product Monitoring](/Product_Monitoring)")
        st.markdown("📈 [Price History](/Price_History)")
        st.markdown("🔔 [Alert Management](/Alert_Management)")
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("PriceWatcher is a tool for tracking product prices on e-commerce websites.")
        st.markdown("Features include:")
        st.markdown("- Automated price monitoring")
        st.markdown("- Custom price alerts")
        st.markdown("- Real-time notifications")
        st.markdown("- Historical data storage")
        st.markdown("- REST API")
    
    # Main content
    st.title("📊 PriceWatcher Dashboard")
    st.write("Welcome to PriceWatcher - your automated price tracking solution.")
    
    # Get session
    session = get_session()
    
    try:
        # Overview metrics
        st.header("System Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Count products
        product_count = session.query(Product).filter(Product.active == True).count()
        col1.metric("Products Tracked", product_count)
        
        # Count stores
        store_count = session.query(Store).count()
        col2.metric("Stores", store_count)
        
        # Count alerts
        alert_count = session.query(PriceAlert).filter(PriceAlert.is_active == True).count()
        col3.metric("Active Alerts", alert_count)
        
        # Count price points in the last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_price_points = session.query(PricePoint).filter(PricePoint.timestamp >= yesterday).count()
        col4.metric("Price Updates (24h)", recent_price_points)
        
        # Price trend summary
        st.header("Price Trend Summary")
        
        # Get all active products
        products = session.query(Product).filter(Product.active == True).all()
        
        if not products:
            st.info("No products being tracked yet. Add products through the API.")
        else:
            # Calculate price trends
            price_trends = []
            for product in products:
                # Get latest price
                latest_price = session.query(PricePoint).filter(
                    PricePoint.product_id == product.id
                ).order_by(PricePoint.timestamp.desc()).first()
                
                # Get price from a week ago
                week_ago = datetime.utcnow() - timedelta(days=7)
                old_price = session.query(PricePoint).filter(
                    PricePoint.product_id == product.id,
                    PricePoint.timestamp <= week_ago
                ).order_by(PricePoint.timestamp.desc()).first()
                
                # If no old price, get the oldest available
                if not old_price:
                    old_price = session.query(PricePoint).filter(
                        PricePoint.product_id == product.id
                    ).order_by(PricePoint.timestamp.asc()).first()
                
                if latest_price and old_price:
                    price_change = ((latest_price.price - old_price.price) / old_price.price) * 100
                    price_trends.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'price_change': price_change,
                        'current_price': latest_price.price,
                        'currency': latest_price.currency
                    })
            
            if price_trends:
                # Create columns for different trend categories
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Biggest Price Drops")
                    # Sort by biggest price drops (negative change)
                    price_drops = sorted(price_trends, key=lambda x: x['price_change'])[:5]
                    
                    if price_drops:
                        for item in price_drops:
                            if item['price_change'] < 0:  # Only show actual drops
                                st.markdown(f"**{item['product_name']}**: {format_price(item['current_price'], item['currency'])} "
                                          f"({item['price_change']:.2f}% ↓)")
                    else:
                        st.info("No price drops detected in the last week.")
                
                with col2:
                    st.subheader("Biggest Price Increases")
                    # Sort by biggest price increases (positive change)
                    price_increases = sorted(price_trends, key=lambda x: x['price_change'], reverse=True)[:5]
                    
                    if price_increases:
                        for item in price_increases:
                            if item['price_change'] > 0:  # Only show actual increases
                                st.markdown(f"**{item['product_name']}**: {format_price(item['current_price'], item['currency'])} "
                                          f"({item['price_change']:.2f}% ↑)")
                    else:
                        st.info("No price increases detected in the last week.")
            
            # Recent price alerts
            st.header("Recent Price Alerts")
            
            # Get alerts that have been triggered (where current price <= target price)
            triggered_alerts = []
            alerts = session.query(PriceAlert).filter(PriceAlert.is_active == True).all()
            
            for alert in alerts:
                product = next((p for p in products if p.id == alert.product_id), None)
                if product:
                    latest_price = session.query(PricePoint).filter(
                        PricePoint.product_id == product.id
                    ).order_by(PricePoint.timestamp.desc()).first()
                    
                    if latest_price and latest_price.price <= alert.target_price:
                        triggered_alerts.append({
                            'alert_id': alert.id,
                            'product_name': product.name,
                            'current_price': latest_price.price,
                            'target_price': alert.target_price,
                            'currency': latest_price.currency,
                            'last_notified': alert.last_notified_at
                        })
            
            if triggered_alerts:
                # Sort by most recent notification
                triggered_alerts = sorted(triggered_alerts, 
                                         key=lambda x: x['last_notified'] if x['last_notified'] else datetime.min, 
                                         reverse=True)
                
                for alert in triggered_alerts[:5]:  # Show top 5
                    st.success(f"**{alert['product_name']}**: Current price {format_price(alert['current_price'], alert['currency'])} "
                             f"has reached target {format_price(alert['target_price'], alert['currency'])}")
            else:
                st.info("No triggered price alerts at the moment.")
            
            # Recent activity chart
            st.header("Recent Activity")
            
            # Get price points from the last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_price_points = session.query(PricePoint).filter(
                PricePoint.timestamp >= thirty_days_ago
            ).all()
            
            if recent_price_points:
                # Group by day
                df = pd.DataFrame([
                    {
                        'date': pp.timestamp.date(),
                        'count': 1
                    }
                    for pp in recent_price_points
                ])
                
                daily_counts = df.groupby('date').count().reset_index()
                
                # Create date range for all days
                date_range = pd.date_range(start=thirty_days_ago.date(), end=datetime.utcnow().date())
                date_df = pd.DataFrame({'date': date_range})
                
                # Merge to include days with no activity
                merged_df = pd.merge(date_df, daily_counts, on='date', how='left').fillna(0)
                
                # Plot activity
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.bar(merged_df['date'], merged_df['count'], color='#1f77b4')
                ax.set_title("Daily Price Tracking Activity (Last 30 Days)")
                ax.set_xlabel("Date")
                ax.set_ylabel("Number of Price Updates")
                ax.grid(axis='y', linestyle='--', alpha=0.7)
                
                # Format x-axis to show fewer dates
                ax.xaxis.set_major_locator(plt.MaxNLocator(10))
                fig.autofmt_xdate(rotation=45)
                
                st.pyplot(fig)
            else:
                st.info("No recent price tracking activity in the last 30 days.")
            
            # Quick product view
            st.header("Quick Product View")
            
            # Show top 5 most recently updated products
            recent_products = []
            for product in products:
                latest_price = session.query(PricePoint).filter(
                    PricePoint.product_id == product.id
                ).order_by(PricePoint.timestamp.desc()).first()
                
                if latest_price:
                    recent_products.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'price': latest_price.price,
                        'currency': latest_price.currency,
                        'in_stock': latest_price.in_stock,
                        'timestamp': latest_price.timestamp
                    })
            
            if recent_products:
                # Sort by most recent update
                recent_products = sorted(recent_products, key=lambda x: x['timestamp'], reverse=True)[:5]
                
                # Create columns for each product
                cols = st.columns(len(recent_products))
                
                for i, product in enumerate(recent_products):
                    with cols[i]:
                        st.subheader(product['product_name'])
                        st.metric(
                            "Current Price", 
                            format_price(product['price'], product['currency'])
                        )
                        st.write(f"**Status:** {'In Stock ✅' if product['in_stock'] else 'Out of Stock ❌'}")
                        st.write(f"**Updated:** {product['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                        st.button(f"View Details", key=f"view_{product['product_id']}", 
                                 help=f"Go to product details page for {product['product_name']}")
            else:
                st.info("No product price data available yet.")

    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
    finally:
        session.close()
    
    # Footer
    st.markdown("---")
    st.caption("PriceWatcher Dashboard | Data refreshes automatically")

if __name__ == "__main__":
    main()
