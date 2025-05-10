"""
Integration connector with Group 29's Intelligent Demand Forecasting system.
This module handles data exchange between our Supplier Ranking system and
the Demand Forecasting system using Time Series Analysis, Prophet, and LSTMs.
"""

import json
import logging
import requests
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Union, Any
import os
import random
from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

class Group29Connector:
    """
    Connector class for integrating with Group 29's Demand Forecasting system.
    Responsible for retrieving forecasts that can influence supplier rankings.
    """
    
    def __init__(self, use_dummy_data=True):
        """
        Initialize the connector with configuration options.
        
        Args:
            use_dummy_data: Flag to use dummy data for testing
        """
        # Use environment variable first, then settings
        self.base_url = os.environ.get('GROUP29_SERVICE_URL', 'http://group29-service-api/api/v1')
        
        # Get authentication credentials from settings or environment
        self.auth_token = ''
        
        # Headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        # Connection timeout settings
        self.timeout = 10  # seconds
        
        # Flag to use dummy data for testing
        self.use_dummy_data = use_dummy_data
        
        logger.info(f"Initialized Group29Connector with base URL: {self.base_url}")
    
    def get_supplier_forecast_accuracy(self, supplier_id):
        """
        Get forecast accuracy metrics for a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            dict: Dictionary containing forecast accuracy metrics
        """
        if self.use_dummy_data:
            # Generate random but stable accuracy score for each supplier
            random.seed(supplier_id)  # Use supplier_id as seed for consistent random numbers
            
            accuracy_base = 85 + random.randint(0, 10)  # Base accuracy between 85-95%
            
            return {
                "supplier_id": supplier_id,
                "accuracy": accuracy_base + (5 if supplier_id % 3 == 0 else 0),  # Boost some suppliers
                "consistency": random.uniform(7.5, 9.5),
                "seasonal_adjustment_score": random.uniform(7.0, 9.0),
                "lead_time_forecast_accuracy": random.uniform(80.0, 95.0),
                "demand_volatility_score": random.uniform(6.0, 9.0),
                "overall_forecast_score": random.uniform(7.5, 9.5)
            }
        
        try:
            response = requests.get(
                f"{self.base_url}/supplier-forecast/{supplier_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching forecast accuracy for supplier {supplier_id}: {str(e)}")
            return {
                "accuracy": 90.0,  # Default value
                "consistency": 8.0,
                "seasonal_adjustment_score": 8.0,
                "lead_time_forecast_accuracy": 85.0,
                "demand_volatility_score": 7.0,
                "overall_forecast_score": 8.0
            }
    
    def get_product_demand_forecast(self, product_id, forecast_period=90):
        """
        Get demand forecast for a specific product
        
        Args:
            product_id (int): ID of the product
            forecast_period (int): Number of days to forecast
            
        Returns:
            dict: Dictionary containing demand forecast data
        """
        if self.use_dummy_data:
            today = date.today()
            
            # Generate random but stable forecast for each product
            random.seed(product_id)  # Use product_id as seed for consistent random numbers
            
            base_demand = 100 + random.randint(0, 900)  # Base demand between 100-1000 units
            growth_factor = random.uniform(0.9, 1.2)   # Random growth/decline factor
            seasonality = random.uniform(0.8, 1.2)     # Random seasonality factor
            
            # Generate forecast data points
            forecast_data = []
            for day in range(1, forecast_period+1):
                # Calculate demand with some randomness and seasonality
                forecast_date = today + timedelta(days=day)
                day_of_week_factor = 1.0 + (0.2 if forecast_date.weekday() < 5 else -0.3)  # Higher on weekdays
                month_factor = 1.0 + (0.1 * (forecast_date.month % 3))  # Quarterly cycle
                
                demand = base_demand * (growth_factor ** (day/90)) * day_of_week_factor * month_factor
                demand *= (1 + random.uniform(-0.1, 0.1))  # Add +/- 10% random noise
                
                forecast_data.append({
                    "date": forecast_date.isoformat(),
                    "predicted_demand": round(demand),
                    "confidence_level": random.uniform(0.7, 0.95)
                })
            
            return {
                "product_id": product_id,
                "forecast_period": forecast_period,
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=forecast_period)).isoformat(),
                "total_predicted_demand": sum(point["predicted_demand"] for point in forecast_data),
                "average_daily_demand": round(sum(point["predicted_demand"] for point in forecast_data) / forecast_period),
                "forecast_data": forecast_data,
                "forecast_accuracy": random.uniform(85.0, 95.0),
                "last_updated": datetime.now().isoformat()
            }
        
        try:
            response = requests.get(
                f"{self.base_url}/product-forecast/{product_id}",
                params={"forecast_period": forecast_period},
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching demand forecast for product {product_id}: {str(e)}")
            return {
                "product_id": product_id,
                "error": "Failed to fetch forecast data",
                "message": str(e)
            }
    
    def get_supplier_demand_forecast(self, supplier_id: int,
                                    horizon_days: int = 90) -> Dict[str, Any]:
        """
        Retrieve aggregated demand forecast for all products from a specific supplier.
        
        Args:
            supplier_id: ID of the supplier
            horizon_days: Number of days to forecast ahead
            
        Returns:
            Dictionary containing forecast data
            
        Raises:
            ConnectionError: If unable to connect to the forecasting service
            ValueError: If the response is invalid
        """
        try:
            endpoint = f"forecasts/suppliers/{supplier_id}/"
            params = {"horizon_days": horizon_days}
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get supplier demand forecast: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 29's forecasting service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from forecasting service")
            raise ValueError("Invalid response from Group 29's forecasting service")
    
    def get_forecast_confidence(self, forecast_id: int) -> Dict[str, Any]:
        """
        Get confidence metrics for a specific forecast.
        
        Args:
            forecast_id: ID of the forecast
            
        Returns:
            Dictionary containing confidence metrics
        """
        try:
            endpoint = f"forecasts/{forecast_id}/confidence/"
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get forecast confidence metrics: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 29's forecasting service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from forecasting service")
            raise ValueError("Invalid response from Group 29's forecasting service")
    
    def get_seasonal_factors(self, product_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get seasonal demand factors that might influence supplier requirements.
        
        Args:
            product_id: Optional filter by product ID
            
        Returns:
            Dictionary containing seasonal factors
        """
        try:
            endpoint = "forecasts/seasonal-factors/"
            params = {}
            if product_id:
                params["product_id"] = product_id
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get seasonal factors: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 29's forecasting service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from forecasting service")
            raise ValueError("Invalid response from Group 29's forecasting service")
    
    def calculate_supply_risk(self, supplier_id: int) -> Dict[str, Any]:
        """
        Calculate supply risk based on demand forecasts and supplier capacity.
        
        Args:
            supplier_id: ID of the supplier
            
        Returns:
            Dictionary containing risk assessment
        """
        try:
            endpoint = "analysis/supply-risk/"
            data = {"supplier_id": supplier_id}
            
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=data,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to calculate supply risk: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 29's forecasting service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from forecasting service")
            raise ValueError("Invalid response from Group 29's forecasting service")
    
    def get_forecast_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current forecasts to help with supplier ranking.
        
        Returns:
            Dictionary containing forecast summaries
        """
        try:
            endpoint = "forecasts/summary/"
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get forecast summary: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 29's forecasting service: {str(e)}")
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from forecasting service")
            raise ValueError("Invalid response from Group 29's forecasting service")
    
    def notify_critical_supplier(self, supplier_id: int, 
                               forecast_data: Dict[str, Any]) -> bool:
        """
        Notify the forecasting system about a critical supplier based on our ranking.
        
        Args:
            supplier_id: ID of the critical supplier
            forecast_data: Data about why this supplier is critical
            
        Returns:
            True if notification was successful
        """
        try:
            endpoint = "notifications/critical-supplier/"
            data = {
                "supplier_id": supplier_id,
                "forecast_data": forecast_data,
                "notified_at": datetime.now().isoformat()
            }
            
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=data,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to notify critical supplier: {str(e)}")
            raise ConnectionError(f"Could not connect to Group 29's forecasting service: {str(e)}")
        
        return False
    
    def test_connection(self):
        """
        Test connection to the Demand Forecasting Service
        Returns True if connection is successful, False otherwise
        """
        if self.use_dummy_data:
            # Always return success when using dummy data
            return True
            
        try:
            # Try to connect to the base URL with auth headers for auth-required endpoints
            response = requests.get(
                f"{self.base_url}/health-check/",
                headers=self.headers,
                timeout=5  # Short timeout for health check
            )
            
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False