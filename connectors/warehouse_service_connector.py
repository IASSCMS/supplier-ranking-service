"""
Connector for the Warehouse Service that handles product data.
"""

import requests
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

class WarehouseServiceConnector:
    """Connector to fetch warehouse and product data from the Warehouse Service"""
    
    def __init__(self, use_dummy_data=True):
        """Initialize connector with base URL and auth credentials from settings"""
        # Use environment variable first, then settings
        self.base_url = os.environ.get('WAREHOUSE_SERVICE_URL', 'http://localhost:8001')
        
        # Fix URL if running in Docker but using localhost
        if 'localhost' in self.base_url and os.environ.get('DOCKER_ENV', 'False') == 'True':
            self.base_url = os.environ.get('WAREHOUSE_SERVICE_URL', 'http://localhost:8001')
            
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
        
        # Create dummy data for testing
        self._create_dummy_data()
        
        logger.info(f"Initialized WarehouseServiceConnector with base URL: {self.base_url}")
    
    def _create_dummy_data(self):
        """Create dummy data for testing"""
        # Dummy products
        self.dummy_products = {
            1: {
                "id": 1,
                "name": "Widget A",
                "sku": "WIDGET-A",
                "description": "Standard widget for industrial use",
                "category": "Widgets",
                "unit_cost": 10.50,
                "stock_quantity": 500,
                "min_stock_level": 100
            },
            2: {
                "id": 2,
                "name": "Widget B",
                "sku": "WIDGET-B",
                "description": "Premium widget for specialized use",
                "category": "Widgets",
                "unit_cost": 15.75,
                "stock_quantity": 250,
                "min_stock_level": 50
            },
            3: {
                "id": 3,
                "name": "Component X",
                "sku": "COMP-X",
                "description": "Essential component for assembly",
                "category": "Components",
                "unit_cost": 5.25,
                "stock_quantity": 1000,
                "min_stock_level": 200
            }
        }
        
        # Dummy supplier-product relationships
        self.dummy_supplier_products = [
            {
                "supplier_id": 3,
                "product_id": 1,
                "supplier_name": "A Supplies Inc.",
                "product_name": "Widget A",
                "unit_price": 9.50,
                "lead_time_days": 5,
                "minimum_order_quantity": 50,
                "maximum_order_quantity": 1000,
                "is_preferred": True
            },
            {
                "supplier_id": 3,
                "product_id": 2,
                "supplier_name": "A Supplies Inc.",
                "product_name": "Widget B",
                "unit_price": 14.75,
                "lead_time_days": 7,
                "minimum_order_quantity": 25,
                "maximum_order_quantity": 500,
                "is_preferred": True
            },
            {
                "supplier_id": 4,
                "product_id": 1,
                "supplier_name": "B Supplies Inc.",
                "product_name": "Widget A",
                "unit_price": 9.80,
                "lead_time_days": 4,
                "minimum_order_quantity": 25,
                "maximum_order_quantity": 800,
                "is_preferred": False
            },
            {
                "supplier_id": 5,
                "product_id": 2,
                "supplier_name": "C Supplies Inc.",
                "product_name": "Widget B",
                "unit_price": 14.50,
                "lead_time_days": 6,
                "minimum_order_quantity": 20,
                "maximum_order_quantity": 600,
                "is_preferred": False
            },
            {
                "supplier_id": 5,
                "product_id": 3,
                "supplier_name": "C Supplies Inc.",
                "product_name": "Component X",
                "unit_price": 4.90,
                "lead_time_days": 3,
                "minimum_order_quantity": 100,
                "maximum_order_quantity": 2000,
                "is_preferred": True
            }
        ]
        
        # Dummy categories
        self.dummy_categories = [
            {"id": 1, "name": "Widgets", "description": "Standard industrial widgets"},
            {"id": 2, "name": "Components", "description": "Assembly components"},
            {"id": 3, "name": "Raw Materials", "description": "Basic raw materials"}
        ]
        
        # Dummy supplier categories (which suppliers provide products in which categories)
        self.dummy_supplier_categories = {
            3: [1, 2],  # A Supplies Inc. provides Widgets and Components
            4: [1],     # B Supplies Inc. provides Widgets only
            5: [2, 3]   # C Supplies Inc. provides Components and Raw Materials
        }
    
    def get_supplier_products(self, supplier_id):
        """Get all products offered by a supplier"""
        if self.use_dummy_data:
            # Filter supplier products by supplier_id
            return [sp for sp in self.dummy_supplier_products if sp['supplier_id'] == supplier_id]
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/supplier-products/",
                params={"supplier_id": supplier_id},
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching supplier products for {supplier_id}: {str(e)}")
            return []
    
    def get_product_suppliers(self, product_id):
        """Get all suppliers that offer a specific product"""
        if self.use_dummy_data:
            # Filter supplier products by product_id
            return [sp for sp in self.dummy_supplier_products if sp['product_id'] == product_id]
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/product-suppliers/{product_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching suppliers for product {product_id}: {str(e)}")
            return []
    
    def get_suppliers_by_product(self, product_id):
        """Get all supplier IDs that offer a specific product"""
        if self.use_dummy_data:
            # Filter supplier products by product_id and return just the supplier IDs
            supplier_products = [sp for sp in self.dummy_supplier_products if str(sp['product_id']) == str(product_id)]
            return [str(sp['supplier_id']) for sp in supplier_products]
        
        try:
            # Convert the product ID to a string to ensure type consistency
            product_id = str(product_id)
            
            response = requests.get(
                f"{self.base_url}/api/v1/suppliers-by-product/{product_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching supplier IDs for product {product_id}: {str(e)}")
            return []
    
    def get_product(self, product_id):
        """Get details for a specific product"""
        if self.use_dummy_data:
            return self.dummy_products.get(product_id)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/products/{product_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching product {product_id}: {str(e)}")
            return None
    
    def get_suppliers_by_category(self, category_id):
        """Get all suppliers that offer products in a specific category"""
        if self.use_dummy_data:
            # Find suppliers that provide products in this category
            suppliers = []
            for supplier_id, categories in self.dummy_supplier_categories.items():
                if category_id in categories:
                    suppliers.append(supplier_id)
            return suppliers
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/suppliers-by-category/{category_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching suppliers for category {category_id}: {str(e)}")
            return []
    
    def test_connection(self):
        """
        Test connection to the Warehouse Service
        Returns True if connection is successful, False otherwise
        """
        if self.use_dummy_data:
            # Always return success when using dummy data
            return True
            
        try:
            # Try to connect to the base URL with auth headers for auth-required endpoints
            response = requests.get(
                f"{self.base_url}/api/v1/health-check/",
                headers=self.headers,
                timeout=5  # Short timeout for health check
            )
            
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False