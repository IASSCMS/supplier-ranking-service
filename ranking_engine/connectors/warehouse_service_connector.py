"""
Connector for the Warehouse Service that handles product data.
"""

import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class WarehouseServiceConnector:
    """Connector to fetch product data from the Warehouse Service"""
    
    def __init__(self):
        """Initialize connector with base URL from settings"""
        self.warehouse_base_url = settings.WAREHOUSE_SERVICE_URL
        self.product_base_url = settings.PRODUCT_SERVICE_URL
        
    def get_supplier_products(self, supplier_id):
        """
        Get products for a supplier from the warehouse service
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            list: List of product dictionaries
        """
        try:
            # Use the correct path from warehouse urls: 'suppliers/<int:supplier_id>/products'
            response = requests.get(f"{self.warehouse_base_url}/api/warehouse/suppliers/{supplier_id}/products")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching products for supplier {supplier_id}: {str(e)}")
            return []
    
    def get_suppliers_by_category(self, category):
        """
        Fetch supplier IDs that offer products in a specific category
        
        Args:
            category (str): Category name
            
        Returns:
            list: List of supplier IDs
        """
        try:
            # Use the correct path from warehouse urls: 'suppliers-by-category'
            response = requests.get(
                f"{self.warehouse_base_url}/api/warehouse/suppliers-by-category?category={category}"
            )
            response.raise_for_status()
            return response.json().get('supplier_ids', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching suppliers for category {category}: {str(e)}")
            return []
    
    # def update_supplier_preferences(self, supplier_id, preferences_data):
    #     """Update preference flags for supplier products"""
        # try:
        #     response = requests.post(
        #         f"{self.base_url}/api/supplier-products/preferences",
        #         json={
        #             'supplier_id': supplier_id,
        #             'preferences': preferences_data
        #         }
        #     )
        #     response.raise_for_status()
        #     return True
        # except requests.exceptions.RequestException as e:
        #     logger.error(f"Error updating preferences for supplier {supplier_id}: {str(e)}")
        #     return False
        
        # Simulated response - always return success for test data
        # logger.info(f"Simulated update of preferences for supplier {supplier_id}: {preferences_data}")
        # return True
        
    def get_product_suppliers(self, product_id):
        """
        Get all suppliers offering a specific product
        
        Args:
            product_id (int): ID of the product
            
        Returns:
            list: List of supplier product dictionaries
        """
        try:
            # Use the supplier-product-list endpoint with filter
            response = requests.get(
                f"{self.product_base_url}/api/product/supplier-products/?product_id={product_id}"
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching suppliers for product {product_id}: {str(e)}")
            return []