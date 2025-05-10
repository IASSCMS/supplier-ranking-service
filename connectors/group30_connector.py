"""
Integration connector with Group 30's Blockchain-Based Order Tracking system.
This module handles data exchange between our Supplier Ranking system and
the Blockchain-Based Order Tracking system using Hyperledger Fabric and IPFS.
"""

import json
import logging
import requests
import os
import random
import time
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from django.conf import settings

# Set up logging
logger = logging.getLogger(__name__)

class Group30Connector:
    """
    Connector class for integrating with Group 30's Blockchain-Based Order Tracking system.
    Responsible for retrieving blockchain data that can be used to evaluate supplier performance.
    """
    
    def __init__(self, use_dummy_data=True):
        """
        Initialize the connector with configuration options.
        
        Args:
            use_dummy_data: Flag to use dummy data for testing
        """
        # Use environment variable first, then settings
        self.base_url = os.environ.get('GROUP30_SERVICE_URL', 'http://group30-quality-api/api/v1')
        
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
        
        logger.info(f"Initialized Group30Connector with base URL: {self.base_url}")
        
        # Generate dummy data for testing if needed
        if self.use_dummy_data:
            self._create_dummy_data()
    
    def _create_dummy_data(self):
        """Create dummy quality data for testing"""
        self.dummy_supplier_quality = {}
        self.dummy_product_quality = {}
        
        # Create dummy data for 20 suppliers
        for supplier_id in range(1, 21):
            # Use supplier_id as seed for consistent random data
            random.seed(supplier_id)
            
            # Generate quality metrics with some variation
            defect_rate = round(random.uniform(0.5, 5.0), 2)
            if supplier_id % 5 == 0:  # Every 5th supplier has higher quality
                defect_rate = round(defect_rate / 2, 2)
            
            return_rate = round(random.uniform(1.0, 10.0), 2)
            if supplier_id % 3 == 0:  # Every 3rd supplier has lower return rate
                return_rate = round(return_rate / 1.5, 2)
            
            # Generate quality scores
            quality_score = round(10 - (defect_rate / 2 + return_rate / 4), 1)
            quality_score = max(min(quality_score, 10.0), 1.0)  # Clamp between 1 and 10
            
            # Generate consistency score
            consistency_score = round(random.uniform(6.0, 9.5), 1)
            
            # Store dummy data
            self.dummy_supplier_quality[supplier_id] = {
                "supplier_id": supplier_id,
                "quality_score": quality_score,
                "defect_rate": defect_rate,
                "return_rate": return_rate,
                "consistency_score": consistency_score,
                "on_time_delivery_quality": round(random.uniform(85, 99), 1),
                "packaging_score": round(random.uniform(7.0, 9.5), 1),
                "last_audit_date": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        
        # Create dummy data for 100 products
        for product_id in range(1, 101):
            # Use product_id as seed for consistent random data
            random.seed(product_id)
            
            # Generate quality metrics with variation
            defect_rate = round(random.uniform(0.2, 4.0), 2)
            return_rate = round(random.uniform(0.5, 8.0), 2)
            
            # Quality score calculation
            quality_score = round(10 - (defect_rate / 2 + return_rate / 3), 1)
            quality_score = max(min(quality_score, 10.0), 1.0)  # Clamp between 1 and 10
            
            # Store dummy data
            self.dummy_product_quality[product_id] = {
                "product_id": product_id,
                "quality_score": quality_score,
                "defect_rate": defect_rate,
                "return_rate": return_rate,
                "customer_satisfaction_score": round(random.uniform(3.0, 4.9), 1),
                "durability_score": round(random.uniform(6.0, 9.8), 1),
                "inspection_pass_rate": round(random.uniform(90, 99.9), 1),
                "last_updated": datetime.now().isoformat()
            }
    
    def get_supplier_quality_metrics(self, supplier_id):
        """
        Get quality metrics for a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            dict: Dictionary containing supplier quality metrics
        """
        if self.use_dummy_data:
            # If we don't have dummy data for this supplier, generate it
            if supplier_id not in self.dummy_supplier_quality:
                random.seed(supplier_id)
                
                defect_rate = round(random.uniform(0.5, 5.0), 2)
                return_rate = round(random.uniform(1.0, 10.0), 2)
                quality_score = round(10 - (defect_rate / 2 + return_rate / 4), 1)
                quality_score = max(min(quality_score, 10.0), 1.0)
                
                self.dummy_supplier_quality[supplier_id] = {
                    "supplier_id": supplier_id,
                    "quality_score": quality_score,
                    "defect_rate": defect_rate,
                    "return_rate": return_rate,
                    "consistency_score": round(random.uniform(6.0, 9.5), 1),
                    "on_time_delivery_quality": round(random.uniform(85, 99), 1),
                    "packaging_score": round(random.uniform(7.0, 9.5), 1),
                    "last_audit_date": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
            
            return self.dummy_supplier_quality[supplier_id]
        
        try:
            response = requests.get(
                f"{self.base_url}/suppliers/{supplier_id}/quality",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching quality metrics for supplier {supplier_id}: {str(e)}")
            # Return default data on error
            return {
                "supplier_id": supplier_id,
                "quality_score": 7.5,
                "defect_rate": 2.0,
                "return_rate": 3.5,
                "consistency_score": 8.0,
                "on_time_delivery_quality": 92.0,
                "packaging_score": 8.5,
                "error": "Failed to fetch real data"
            }
    
    def get_product_quality_metrics(self, product_id):
        """
        Get quality metrics for a specific product
        
        Args:
            product_id (int): ID of the product
            
        Returns:
            dict: Dictionary containing product quality metrics
        """
        if self.use_dummy_data:
            # If we don't have dummy data for this product, generate it
            if product_id not in self.dummy_product_quality:
                random.seed(product_id)
                
                defect_rate = round(random.uniform(0.2, 4.0), 2)
                return_rate = round(random.uniform(0.5, 8.0), 2)
                quality_score = round(10 - (defect_rate / 2 + return_rate / 3), 1)
                quality_score = max(min(quality_score, 10.0), 1.0)
                
                self.dummy_product_quality[product_id] = {
                    "product_id": product_id,
                    "quality_score": quality_score,
                    "defect_rate": defect_rate,
                    "return_rate": return_rate,
                    "customer_satisfaction_score": round(random.uniform(3.0, 4.9), 1),
                    "durability_score": round(random.uniform(6.0, 9.8), 1),
                    "inspection_pass_rate": round(random.uniform(90, 99.9), 1),
                    "last_updated": datetime.now().isoformat()
                }
            
            return self.dummy_product_quality[product_id]
        
        try:
            response = requests.get(
                f"{self.base_url}/products/{product_id}/quality",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching quality metrics for product {product_id}: {str(e)}")
            # Return default data on error
            return {
                "product_id": product_id,
                "quality_score": 7.0,
                "defect_rate": 1.5,
                "return_rate": 2.5,
                "customer_satisfaction_score": 4.1,
                "durability_score": 8.2,
                "inspection_pass_rate": 94.5,
                "error": "Failed to fetch real data"
            }
    
    def get_supplier_products_quality(self, supplier_id):
        """
        Get quality metrics for all products from a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            list: List of product quality metrics for the supplier
        """
        if self.use_dummy_data:
            # Generate dummy product quality data for this supplier
            random.seed(supplier_id)
            num_products = random.randint(5, 15)
            
            products = []
            # Generate product IDs based on supplier ID for consistency
            product_ids = [supplier_id * 100 + i for i in range(1, num_products + 1)]
            
            for product_id in product_ids:
                product_data = self.get_product_quality_metrics(product_id)
                product_data["supplier_id"] = supplier_id
                products.append(product_data)
            
            return products
        
        try:
            response = requests.get(
                f"{self.base_url}/suppliers/{supplier_id}/products/quality",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching product quality for supplier {supplier_id}: {str(e)}")
            # Return empty list on error
            return []
    
    def report_quality_issue(self, supplier_id, product_id, issue_details):
        """
        Report a quality issue for a specific product from a supplier
        
        Args:
            supplier_id (int): ID of the supplier
            product_id (int): ID of the product
            issue_details (dict): Details of the quality issue
            
        Returns:
            dict: Response from the quality service
        """
        if self.use_dummy_data:
            # Simulate a successful response
            return {
                "issue_id": random.randint(10000, 99999),
                "supplier_id": supplier_id,
                "product_id": product_id,
                "status": "reported",
                "created_at": datetime.now().isoformat(),
                "message": "Quality issue reported successfully"
            }
        
        try:
            payload = {
                "supplier_id": supplier_id,
                "product_id": product_id,
                "issue_details": issue_details
            }
            
            response = requests.post(
                f"{self.base_url}/quality-issues/report",
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error reporting quality issue: {str(e)}")
            return {
                "error": "Failed to report quality issue",
                "message": str(e)
            }
    
    def test_connection(self):
        """
        Test connection to the Product Quality Service
        Returns True if connection is successful, False otherwise
        """
        if self.use_dummy_data:
            # Always return success when using dummy data
            return True
            
        try:
            # Try to connect to the base URL with auth headers for auth-required endpoints
            response = requests.get(
                f"{self.base_url}/health-check",
                headers=self.headers,
                timeout=5  # Short timeout for health check
            )
            
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False