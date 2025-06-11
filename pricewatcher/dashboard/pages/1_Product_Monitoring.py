"""
Product Monitoring page for PriceWatcher dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from pricewatcher.database.connection import get_session
from pricewatcher.database.models import Product, PricePoint, Store
from pricewatcher.utils.helpers import format_price

st.set_page_config(
    page_title="Product Monitoring | PriceWatcher",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Product Monitoring")
st.write("Monitor your tracked products and their current prices.")

# Get session
session = get_session()

try:
    # Overview metrics
    st.header("Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Count products
    product_count = session.query(Product).filter(Product.active == True).count()
    col1.metric("Active Products", product_count)
    
    # Count stores
    store_count = session.query(Store).count()
    col2.metric("Stores", store_count)
    
    # Count price points in the last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_price_points = session.query(PricePoint).filter(PricePoint.timestamp >= yesterday).count()
    col3.metric("Price Updates (24h)", recent_price_points)
    
    # Count products with price drops in the last week
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # This is a simplified approach - in a real app, you'd want to optimize this query
    price_drops = 0
    products = session.query(Product).filter(Product.active == True).all()
    for product in products:
        # Get latest price
        latest_price = session.query(PricePoint).filter(
            PricePoint.product_id == product.id
        ).order_by(PricePoint.timestamp.desc()).first()
        
        # Get price from a week ago (or oldest if less than a week)
        old_price = session.query(PricePoint).filter(
            PricePoint.product_id == product.id,
            PricePoint.timestamp <= week_ago
        ).order_by(PricePoint.timestamp.desc()).first()
        
        # If no old price, get the oldest available
        if not old_price:
            old_price = session.query(PricePoint).filter(
                PricePoint.product_id == product.id
            ).order_by(PricePoint.timestamp.asc()).first()
        
        if latest_price and old_price and latest_price.price < old_price.price:
            price_drops += 1
    
    col4.metric("Price Drops (7d)", price_drops)
    
    # Filter options
    st.header("Product List")
    
    col1, col2 = st.columns(2)
    
    # Store filter
    stores = session.query(Store).all()
    store_options = ["All Stores"] + [store.name for store in stores]
    selected_store = col1.selectbox("Filter by Store", options=store_options)
    
    # Stock status filter
    stock_options = ["All Products", "In Stock Only", "Out of Stock Only"]
    selected_stock = col2.selectbox("Filter by Stock Status", options=stock_options)
    
    # Get products with filters
    query = session.query(Product).filter(Product.active == True)
    
    # Apply store filter
    if selected_store != "All Stores":
        store_id = next((store.id for store in stores if store.name == selected_store), None)
        if store_id:
            query = query.filter(Product.store_id == store_id)
    
    products = query.all()
    
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
            
            # Apply stock filter
            if (selected_stock == "In Stock Only" and not in_stock) or \
               (selected_stock == "Out of Stock Only" and in_stock):
                continue
            
            # Get price from a week ago for comparison
            week_ago = datetime.utcnow() - timedelta(days=7)
            old_price = session.query(PricePoint).filter(
                PricePoint.product_id == product.id,
                PricePoint.timestamp <= week_ago
            ).order_by(PricePoint.timestamp.desc()).first()
            
            # If no old price from a week ago, get the oldest available
            if not old_price:
                old_price = session.query(PricePoint).filter(
                    PricePoint.product_id == product.id
                ).order_by(PricePoint.timestamp.asc()).first()
            
            old_price_formatted = format_price(old_price.price, old_price.currency) if old_price else "N/A"
            
            # Calculate price change
            price_change = None
            if latest_price and old_price:
                price_change = ((latest_price.price - old_price.price) / old_price.price) * 100
            
            product_data.append({
                "ID": product.id,
                "Name": product.name,
                "Store": store.name if store else "Unknown",
                "Current Price": price_formatted,
                "Previous Price": old_price_formatted,
                "Price Change": f"{price_change:.2f}%" if price_change is not None else "N/A",
                "In Stock": "✅" if in_stock else "❌",
                "Last Updated": latest_price.timestamp.strftime("%Y-%m-%d %H:%M") if latest_price else "N/A",
                "URL": product.url
            })
        
        # Show product table
        df = pd.DataFrame(product_data)
        
        # Add color to price change column
        def highlight_price_change(val):
            if isinstance(val, str) and val.endswith('%'):
                try:
                    value = float(val.strip('%'))
                    if value < 0:
                        return 'color: green'  # Price drop (good)
                    elif value > 0:
                        return 'color: red'    # Price increase (bad)
                except:
                    pass
            return ''
        
        # Display the dataframe with styling
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
                "Current Price": st.column_config.TextColumn(
                    "Current Price",
                    width="small",
                ),
                "Previous Price": st.column_config.TextColumn(
                    "Previous Price",
                    width="small",
                ),
                "Price Change": st.column_config.TextColumn(
                    "7-Day Change",
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
                "URL": st.column_config.LinkColumn(
                    "Product Link",
                    width="small",
                    display_text="View"
                )
            },
            use_container_width=True
        )
        
        # Product detail view
        st.header("Product Details")
        selected_product = st.selectbox(
            "Select a product to view details",
            options=[p.id for p in products],
            format_func=lambda x: next((p.name for p in products if p.id == x), str(x))
        )
        
        # Show product details
        if selected_product:
            product = next((p for p in products if p.id == selected_product), None)
            if product:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if product.image_url:
                        st.image(product.image_url, width=200)
                    else:
                        st.info("No image available")
                
                with col2:
                    st.subheader(product.name)
                    st.write(f"**Store:** {next((s.name for s in stores if s.id == product.store_id), 'Unknown')}")
                    st.write(f"**URL:** [{product.url}]({product.url})")
                    if product.description:
                        st.write(f"**Description:** {product.description}")
                    
                    # Get latest price
                    latest_price = session.query(PricePoint).filter(
                        PricePoint.product_id == product.id
                    ).order_by(PricePoint.timestamp.desc()).first()
                    
                    if latest_price:
                        st.write(f"**Current Price:** {format_price(latest_price.price, latest_price.currency)}")
                        st.write(f"**In Stock:** {'Yes' if latest_price.in_stock else 'No'}")
                        st.write(f"**Last Updated:** {latest_price.timestamp.strftime('%Y-%m-%d %H:%M')}")

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
finally:
    session.close()
