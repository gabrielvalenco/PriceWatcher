"""
API server for PriceWatcher
"""
import os
import logging
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

from pricewatcher.database.connection import get_session, init_db
from pricewatcher.database.models import Product, Store, PricePoint, PriceAlert
from pricewatcher.scrapers.manager import ScraperManager

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PriceWatcher API",
    description="API for tracking product prices on e-commerce websites",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create scraper manager
scraper_manager = ScraperManager()

# Pydantic models for request and response
class ProductCreate(BaseModel):
    """Product creation model"""
    url: HttpUrl
    
class ProductResponse(BaseModel):
    """Product response model"""
    id: int
    name: str
    url: str
    image_url: Optional[str] = None
    store_name: str
    current_price: Optional[float] = None
    currency: str = "USD"
    in_stock: bool = True
    
class PriceAlertCreate(BaseModel):
    """Price alert creation model"""
    product_id: int
    target_price: float
    notification_email: Optional[str] = None
    notification_phone: Optional[str] = None
    notification_telegram: Optional[str] = None
    
class PriceAlertResponse(BaseModel):
    """Price alert response model"""
    id: int
    product_id: int
    product_name: str
    target_price: float
    current_price: Optional[float] = None
    is_active: bool
    
class PriceHistoryResponse(BaseModel):
    """Price history response model"""
    product_id: int
    product_name: str
    prices: List[dict]

# Initialize database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the database on startup"""
    init_db()

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to the PriceWatcher API"}

@app.post("/products/", response_model=ProductResponse)
async def create_product(product: ProductCreate, background_tasks: BackgroundTasks):
    """
    Create a new product to track
    """
    session = get_session()
    try:
        # Check if product URL already exists
        existing = session.query(Product).filter(Product.url == str(product.url)).first()
        if existing:
            product_info = get_product_response(existing.id, session)
            session.close()
            return product_info
            
        # Fetch product information
        product_data = scraper_manager.scrape_product(str(product.url))
        if not product_data or 'name' not in product_data or 'store_name' not in product_data:
            session.close()
            raise HTTPException(status_code=400, detail="Failed to fetch product data or unsupported website")
            
        # Get or create store
        store = session.query(Store).filter(Store.name == product_data['store_name']).first()
        if not store:
            store = Store(
                name=product_data['store_name'],
                url=f"https://{product_data['store_name'].lower()}.com",  # Default URL
                scraper_class=f"{product_data['store_name']}Scraper"
            )
            session.add(store)
            session.flush()
            
        # Create new product
        new_product = Product(
            name=product_data['name'],
            url=str(product.url),
            image_url=product_data.get('image_url'),
            description=product_data.get('description'),
            store_id=store.id
        )
        session.add(new_product)
        session.flush()
        
        # Create initial price point
        if 'price' in product_data:
            price_point = PricePoint(
                product_id=new_product.id,
                price=product_data['price'],
                currency=product_data.get('currency', 'USD'),
                in_stock=product_data.get('in_stock', True)
            )
            session.add(price_point)
            
        session.commit()
        
        # Prepare response
        response = ProductResponse(
            id=new_product.id,
            name=new_product.name,
            url=new_product.url,
            image_url=new_product.image_url,
            store_name=store.name,
            current_price=product_data.get('price'),
            currency=product_data.get('currency', 'USD'),
            in_stock=product_data.get('in_stock', True)
        )
        
        return response
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        session.close()
        
@app.get("/products/", response_model=List[ProductResponse])
async def list_products():
    """
    List all tracked products
    """
    session = get_session()
    try:
        products = session.query(Product).filter(Product.active == True).all()
        
        result = []
        for product in products:
            result.append(get_product_response(product.id, session))
            
        return result
        
    except Exception as e:
        logger.error(f"Error listing products: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        session.close()
        
@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    """
    Get details for a specific product
    """
    session = get_session()
    try:
        return get_product_response(product_id, session)
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        session.close()
        
@app.delete("/products/{product_id}")
async def delete_product(product_id: int):
    """
    Delete a product (soft delete by setting active=False)
    """
    session = get_session()
    try:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
            
        product.active = False
        session.commit()
        
        return {"message": "Product deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        session.close()
        
@app.post("/price-alerts/", response_model=PriceAlertResponse)
async def create_price_alert(alert: PriceAlertCreate):
    """
    Create a new price alert for a product
    """
    session = get_session()
    try:
        # Check if product exists
        product = session.query(Product).filter(Product.id == alert.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
            
        # Create alert
        new_alert = PriceAlert(
            product_id=alert.product_id,
            target_price=alert.target_price,
            notification_email=alert.notification_email,
            notification_phone=alert.notification_phone,
            notification_telegram=alert.notification_telegram
        )
        session.add(new_alert)
        session.commit()
        
        # Get latest price
        latest_price = session.query(PricePoint).filter(
            PricePoint.product_id == alert.product_id
        ).order_by(PricePoint.timestamp.desc()).first()
        
        return PriceAlertResponse(
            id=new_alert.id,
            product_id=new_alert.product_id,
            product_name=product.name,
            target_price=new_alert.target_price,
            current_price=latest_price.price if latest_price else None,
            is_active=new_alert.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating price alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        session.close()
        
@app.get("/price-history/{product_id}", response_model=PriceHistoryResponse)
async def get_price_history(product_id: int):
    """
    Get price history for a product
    """
    session = get_session()
    try:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
            
        price_points = session.query(PricePoint).filter(
            PricePoint.product_id == product_id
        ).order_by(PricePoint.timestamp.asc()).all()
        
        prices = []
        for point in price_points:
            prices.append({
                "price": point.price,
                "currency": point.currency,
                "in_stock": point.in_stock,
                "timestamp": point.timestamp.isoformat()
            })
            
        return PriceHistoryResponse(
            product_id=product.id,
            product_name=product.name,
            prices=prices
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price history for product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        session.close()

def get_product_response(product_id: int, session) -> ProductResponse:
    """
    Helper function to get a product response
    """
    product = session.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    # Get store
    store = session.query(Store).filter(Store.id == product.store_id).first()
    
    # Get latest price
    latest_price = session.query(PricePoint).filter(
        PricePoint.product_id == product_id
    ).order_by(PricePoint.timestamp.desc()).first()
    
    return ProductResponse(
        id=product.id,
        name=product.name,
        url=product.url,
        image_url=product.image_url,
        store_name=store.name if store else "Unknown",
        current_price=latest_price.price if latest_price else None,
        currency=latest_price.currency if latest_price else "USD",
        in_stock=latest_price.in_stock if latest_price else True
    )

def start_api():
    """
    Start the FastAPI server
    """
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
