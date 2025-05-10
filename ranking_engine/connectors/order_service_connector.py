"""
Order Service Connector - Handles communication with the Order Service

This connector provides methods to interact with the Order Service API,
which manages orders, transactions, and supplier performance data.
"""

import logging
import requests
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)

class OrderServiceConnector:
    """Connector for Order Service API"""
    
    def __init__(self):
        """Initialize connector with base URL from settings"""
        self.base_url = settings.ORDER_SERVICE_URL
        logger.info(f"Initialized OrderServiceConnector with base URL: {self.base_url}")
    
    def get_supplier_transactions(self, supplier_id, start_date=None, status=None, has_delivery_date=False):
        """
        Get transactions for a supplier
        
        Args:
            supplier_id (int): Supplier ID
            start_date (datetime): Start date for filtering
            status (list): List of statuses to filter by
            has_delivery_date (bool): Whether to only include transactions with delivery dates
            
        Returns:
            list: List of transaction dictionaries
        """
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date.isoformat()
            if status:
                params['status'] = ','.join(status)
            if has_delivery_date:
                params['has_delivery_date'] = 'true'
                
            response = requests.get(
                f"{self.base_url}/suppliers/{supplier_id}/transactions",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting transactions for supplier {supplier_id}: {str(e)}")
            return []
    
    def get_supplier_performance_records(self, supplier_id, start_date=None):
        """
        Get performance records for a supplier
        
        Args:
            supplier_id (int): Supplier ID
            start_date (datetime): Start date for filtering
            
        Returns:
            list: List of performance record dictionaries
        """
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date.isoformat()
                
            response = requests.get(
                f"{self.base_url}/suppliers/{supplier_id}/performance",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting performance records for supplier {supplier_id}: {str(e)}")
            return []
    
    def get_supplier_performance(self, supplier_id, start_date=None):
        """
        Get aggregated performance data for a supplier
        
        Args:
            supplier_id (int): Supplier ID
            start_date (datetime): Start date for filtering
            
        Returns:
            dict: Dictionary of performance metrics
        """
        try:
            params = {}
            if start_date:
                params['start_date'] = start_date.isoformat()
                
            response = requests.get(
                f"{self.base_url}/suppliers/{supplier_id}/performance/summary",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting performance summary for supplier {supplier_id}: {str(e)}")
            return {}
    
    def get_supplier_category_performance(self, supplier_id):
        """
        Get supplier performance grouped by product category
        
        Args:
            supplier_id (int): Supplier ID
            
        Returns:
            dict: Dictionary of performance metrics by category
        """
        try:
            response = requests.get(f"{self.base_url}/suppliers/{supplier_id}/performance/categories")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting category performance for supplier {supplier_id}: {str(e)}")
            return {} 