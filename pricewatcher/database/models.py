"""
Database models for the PriceWatcher application
"""
import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Product(Base):
    """Product model representing items being tracked"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    image_url = Column(String(2048), nullable=True)
    description = Column(Text, nullable=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    active = Column(Boolean, default=True)
    
    # Relationships
    store = relationship("Store", back_populates="products")
    price_points = relationship("PricePoint", back_populates="product", cascade="all, delete-orphan")
    alerts = relationship("PriceAlert", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name})>"


class Store(Base):
    """Store model representing e-commerce websites"""
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    logo_url = Column(String(2048), nullable=True)
    scraper_class = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    active = Column(Boolean, default=True)
    
    # Relationships
    products = relationship("Product", back_populates="store")
    
    def __repr__(self):
        return f"<Store(id={self.id}, name={self.name})>"


class PricePoint(Base):
    """PricePoint model for storing historical price data"""
    __tablename__ = "price_points"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    in_stock = Column(Boolean, default=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationship
    product = relationship("Product", back_populates="price_points")
    
    def __repr__(self):
        return f"<PricePoint(product_id={self.product_id}, price={self.price}, timestamp={self.timestamp})>"


class PriceAlert(Base):
    """PriceAlert model for storing user alert preferences"""
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    target_price = Column(Float, nullable=False)
    notification_email = Column(String(255), nullable=True)
    notification_phone = Column(String(50), nullable=True)
    notification_telegram = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    last_notified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationship
    product = relationship("Product", back_populates="alerts")
    
    def __repr__(self):
        return f"<PriceAlert(product_id={self.product_id}, target_price={self.target_price})>"
