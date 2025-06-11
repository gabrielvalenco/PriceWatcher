"""
Alert Management page for PriceWatcher dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from pricewatcher.database.connection import get_session
from pricewatcher.database.models import Product, PricePoint, PriceAlert, Store
from pricewatcher.utils.helpers import format_price

st.set_page_config(
    page_title="Alert Management | PriceWatcher",
    page_icon="🔔",
    layout="wide"
)

st.title("🔔 Alert Management")
st.write("Create and manage price alerts for your tracked products.")

# Get session
session = get_session()

try:
    # Get all active products
    products = session.query(Product).filter(Product.active == True).all()
    
    if not products:
        st.info("No products being tracked yet. Add products through the API.")
    else:
        # Display existing alerts
        st.header("Current Alerts")
        
        alerts = session.query(PriceAlert).all()
        
        if not alerts:
            st.info("No price alerts have been set up yet.")
        else:
            # Convert to list of dicts for display
            alert_data = []
            for alert in alerts:
                # Get product details
                product = next((p for p in products if p.id == alert.product_id), None)
                if not product:
                    continue
                
                # Get latest price
                latest_price = session.query(PricePoint).filter(
                    PricePoint.product_id == product.id
                ).order_by(PricePoint.timestamp.desc()).first()
                
                current_price = latest_price.price if latest_price else None
                currency = latest_price.currency if latest_price else "USD"
                
                # Calculate price difference
                price_diff = None
                price_diff_percent = None
                if current_price:
                    price_diff = current_price - alert.target_price
                    price_diff_percent = (price_diff / alert.target_price) * 100
                
                # Determine status
                status = "Unknown"
                if current_price:
                    if current_price <= alert.target_price:
                        status = "✅ Target Reached"
                    else:
                        status = f"⏳ {format_price(price_diff, currency)} to go ({price_diff_percent:.1f}%)"
                
                # Determine notification methods
                notification_methods = []
                if alert.notification_email:
                    notification_methods.append("Email")
                if alert.notification_phone:
                    notification_methods.append("SMS")
                if alert.notification_telegram:
                    notification_methods.append("Telegram")
                
                alert_data.append({
                    "ID": alert.id,
                    "Product": product.name,
                    "Target Price": format_price(alert.target_price, currency),
                    "Current Price": format_price(current_price, currency) if current_price else "N/A",
                    "Status": status,
                    "Notifications": ", ".join(notification_methods) if notification_methods else "None",
                    "Active": alert.is_active,
                    "Last Notified": alert.last_notified_at.strftime("%Y-%m-%d %H:%M") if alert.last_notified_at else "Never"
                })
            
            # Show alerts table
            df = pd.DataFrame(alert_data)
            st.dataframe(
                df,
                column_config={
                    "ID": st.column_config.NumberColumn(
                        "ID",
                        help="Alert ID",
                        width="small",
                    ),
                    "Product": st.column_config.TextColumn(
                        "Product",
                        width="medium",
                    ),
                    "Target Price": st.column_config.TextColumn(
                        "Target Price",
                        width="small",
                    ),
                    "Current Price": st.column_config.TextColumn(
                        "Current Price",
                        width="small",
                    ),
                    "Status": st.column_config.TextColumn(
                        "Status",
                        width="medium",
                    ),
                    "Notifications": st.column_config.TextColumn(
                        "Notification Methods",
                        width="medium",
                    ),
                    "Active": st.column_config.CheckboxColumn(
                        "Active",
                        width="small",
                    ),
                    "Last Notified": st.column_config.TextColumn(
                        "Last Notified",
                        width="medium",
                    ),
                },
                use_container_width=True
            )
            
            # Alert management
            st.header("Manage Alerts")
            
            # Select alert to manage
            selected_alert_id = st.selectbox(
                "Select an alert to manage",
                options=[alert.id for alert in alerts],
                format_func=lambda x: f"Alert #{x} - {next((a.product.name for a in alerts if a.id == x), 'Unknown')}"
            )
            
            # Get selected alert
            selected_alert = next((a for a in alerts if a.id == selected_alert_id), None)
            
            if selected_alert:
                # Display alert details
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Alert Details")
                    st.write(f"**Product:** {selected_alert.product.name}")
                    st.write(f"**Target Price:** {format_price(selected_alert.target_price, currency)}")
                    st.write(f"**Status:** {'Active' if selected_alert.is_active else 'Inactive'}")
                    st.write(f"**Created:** {selected_alert.created_at.strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**Last Notified:** {selected_alert.last_notified_at.strftime('%Y-%m-%d %H:%M') if selected_alert.last_notified_at else 'Never'}")
                
                with col2:
                    st.subheader("Notification Settings")
                    st.write(f"**Email:** {selected_alert.notification_email or 'Not set'}")
                    st.write(f"**Phone:** {selected_alert.notification_phone or 'Not set'}")
                    st.write(f"**Telegram:** {selected_alert.notification_telegram or 'Not set'}")
                
                # Alert actions
                st.subheader("Actions")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Toggle active status
                    new_status = st.checkbox("Active", value=selected_alert.is_active, key=f"active_{selected_alert_id}")
                    
                    if new_status != selected_alert.is_active:
                        selected_alert.is_active = new_status
                        session.commit()
                        st.success(f"Alert status updated to {'active' if new_status else 'inactive'}")
                
                with col2:
                    # Delete alert
                    if st.button("Delete Alert", key=f"delete_{selected_alert_id}"):
                        session.delete(selected_alert)
                        session.commit()
                        st.success("Alert deleted successfully")
                        st.rerun()
        
        # Create new alert
        st.header("Create New Alert")
        
        with st.form("new_alert_form"):
            # Product selection
            product_id = st.selectbox(
                "Select Product",
                options=[p.id for p in products],
                format_func=lambda x: next((p.name for p in products if p.id == x), str(x))
            )
            
            # Get current price for reference
            selected_product = next((p for p in products if p.id == product_id), None)
            latest_price = None
            currency = "USD"
            
            if selected_product:
                latest_price = session.query(PricePoint).filter(
                    PricePoint.product_id == selected_product.id
                ).order_by(PricePoint.timestamp.desc()).first()
                
                if latest_price:
                    currency = latest_price.currency
                    st.info(f"Current price: {format_price(latest_price.price, currency)}")
            
            # Target price
            target_price = st.number_input(
                "Target Price",
                min_value=0.01,
                value=latest_price.price * 0.9 if latest_price else 1.0,  # Default to 10% below current price
                step=0.01,
                format="%.2f",
                help="You will be notified when the price drops to or below this value"
            )
            
            # Notification methods
            st.subheader("Notification Methods")
            st.write("Select at least one notification method:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                notification_email = st.text_input("Email Address")
            
            with col2:
                notification_phone = st.text_input("Phone Number (with country code)")
            
            notification_telegram = st.text_input("Telegram Username or Chat ID")
            
            # Submit button
            submitted = st.form_submit_button("Create Alert")
            
            if submitted:
                # Validate form
                if not (notification_email or notification_phone or notification_telegram):
                    st.error("Please select at least one notification method")
                else:
                    # Create new alert
                    new_alert = PriceAlert(
                        product_id=product_id,
                        target_price=target_price,
                        notification_email=notification_email if notification_email else None,
                        notification_phone=notification_phone if notification_phone else None,
                        notification_telegram=notification_telegram if notification_telegram else None,
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    
                    session.add(new_alert)
                    session.commit()
                    
                    st.success("Alert created successfully!")
                    st.rerun()

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
finally:
    session.close()
