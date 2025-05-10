import requests
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

class UserServiceConnector:
    """Connector to fetch supplier data from the User Service"""
    
    def __init__(self, use_dummy_data=True):
        """Initialize connector with base URL and auth credentials from settings"""
        # Use environment variable first, then settings
        self.base_url = os.environ.get('AUTH_SERVICE_URL', 'http://localhost:8000')
        
        # Fix URL if running in Docker but using localhost
        if 'localhost' in self.base_url and os.environ.get('DOCKER_ENV', 'False') == 'True':
            self.base_url = os.environ.get('AUTH_SERVICE_URL', 'http://localhost:8000')
            
        # Get authentication credentials from settings or environment
        self.auth_token = ''
        
        # Change from Api-Key to Bearer token for authentication to match JWTAuthentication
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        # Connection timeout settings
        self.timeout = 10  # seconds
        
        # Flag to use dummy data for testing
        self.use_dummy_data = use_dummy_data
        
        logger.info(f"Initialized UserServiceConnector with base URL: {self.base_url}")
        
    def get_active_suppliers(self):
        """Fetch all active suppliers from User Service"""
        if self.use_dummy_data:
            return [
                {
                    "id": 3,
                    "user": {
                        "id": 3,
                        "username": "supplier",
                        "email": "supplier@example.com",
                        "first_name": "Supply",
                        "last_name": "Manager",
                        "is_active": True
                    },
                    "company_name": "A Supplies Inc.",
                    "code": "SUP-288",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10635",
                    "compliance_score": 4.8,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                },
                {
                    "id": 4,
                    "user": {
                        "id": 4,
                        "username": "vendor",
                        "email": "vendor@example.com",
                        "first_name": "Vendor",
                        "last_name": "Shop",
                        "is_active": True
                    },
                    "company_name": "B Supplies Inc.",
                    "code": "SUP-289",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10636",
                    "compliance_score": 4.8,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                },
                {
                    "id": 5,
                    "user": {
                        "id": 5,
                        "username": "warehouse",
                        "email": "warehouse@example.com",
                        "first_name": "Warehouse",
                        "last_name": "Manager",
                        "is_active": True
                    },
                    "company_name": "C Supplies Inc.",
                    "code": "SUP-290",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10636",
                    "compliance_score": 5.0,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                }
            ]
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/suppliers/?active=true", 
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching active suppliers: {str(e)}")
            return []
    
    def get_active_supplier_count(self):
        """Get the count of active suppliers"""
        if self.use_dummy_data:
            return 3  # Count of suppliers in our dummy data
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/suppliers/count/?active=true",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get('count', 0)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching supplier count: {str(e)}")
            return 0
            
    def get_supplier_by_id(self, supplier_id):
        """Fetch a specific supplier by ID"""
        if self.use_dummy_data:
            dummy_suppliers = {
                3: {
                    "user": {
                        "id": 3,
                        "username": "supplier",
                        "email": "supplier@example.com",
                        "first_name": "Supply",
                        "last_name": "Manager",
                        "is_active": True
                    },
                    "company_name": "A Supplies Inc.",
                    "code": "SUP-288",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10635",
                    "compliance_score": 4.8,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                },
                4: {
                    "user": {
                        "id": 4,
                        "username": "vendor",
                        "email": "vendor@example.com",
                        "first_name": "Vendor",
                        "last_name": "Shop",
                        "is_active": True
                    },
                    "company_name": "B Supplies Inc.",
                    "code": "SUP-289",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10636",
                    "compliance_score": 5,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                },
                5: {
                    "user": {
                        "id": 5,
                        "username": "warehouse",
                        "email": "warehouse@example.com",
                        "first_name": "Warehouse",
                        "last_name": "Manager",
                        "is_active": True
                    },
                    "company_name": "C Supplies Inc.",
                    "code": "SUP-290",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10636",
                    "compliance_score": 3.0,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                }
            }
            return dummy_suppliers.get(supplier_id, None)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/suppliers/{supplier_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching supplier {supplier_id}: {str(e)}")
            return None
        
    def get_supplier_info(self, supplier_id):
        """
        Get detailed information about a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            dict: Supplier details including compliance score
        """
        if self.use_dummy_data:
            dummy_info = {
                3: {
                    "user": {
                        "id": 3,
                        "username": "supplier",
                        "email": "supplier@example.com",
                        "first_name": "Supply",
                        "last_name": "Manager",
                        "is_active": True
                    },
                    "company_name": "A Supplies Inc.",
                    "code": "SUP-288",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10635",
                    "compliance_score": 4.8,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                },
                4: {
                    "user": {
                        "id": 4,
                        "username": "vendor",
                        "email": "vendor@example.com",
                        "first_name": "Vendor",
                        "last_name": "Shop",
                        "is_active": True
                    },
                    "company_name": "B Supplies Inc.",
                    "code": "SUP-289",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10636",
                    "compliance_score": 4.8,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                },
                5: {
                    "user": {
                        "id": 5,
                        "username": "warehouse",
                        "email": "warehouse@example.com",
                        "first_name": "Warehouse",
                        "last_name": "Manager",
                        "is_active": True
                    },
                    "company_name": "C Supplies Inc.",
                    "code": "SUP-290",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10636",
                    "compliance_score": 5.0,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                }
            }
            return dummy_info.get(supplier_id, None)
            
        try:
            # First try to get detailed supplier info from the dedicated endpoint
            url = f"{self.base_url}/api/v1/suppliers/{supplier_id}/info/"
            logger.debug(f"Making request to: {url}")
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            # If info endpoint fails, fall back to standard supplier endpoint
            if response.status_code != 200:
                logger.warning(f"Info endpoint failed, falling back to standard supplier endpoint for {supplier_id}")
                return self.get_supplier_by_id(supplier_id)
            
            supplier_info = response.json()
            return supplier_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching supplier info {supplier_id}: {str(e)}")
            # For debugging, log more details
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text[:200]}")
            return None
            
    def get_all_suppliers(self):
        """
        Get all suppliers regardless of active status
        
        Returns:
            list: List of supplier dictionaries
        """
        if self.use_dummy_data:
            # Return all suppliers from our dummy data
            return [
                {
                    "id": 3,
                    "user": {
                        "id": 3,
                        "username": "supplier",
                        "email": "supplier@example.com",
                        "first_name": "Supply",
                        "last_name": "Manager",
                        "is_active": True
                    },
                    "company_name": "A Supplies Inc.",
                    "code": "SUP-288",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10635",
                    "compliance_score": 4.8,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                },
                {
                    "id": 4,
                    "user": {
                        "id": 4,
                        "username": "vendor",
                        "email": "vendor@example.com",
                        "first_name": "Vendor",
                        "last_name": "Shop",
                        "is_active": True
                    },
                    "company_name": "B Supplies Inc.",
                    "code": "SUP-289",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10636",
                    "compliance_score": 4.8,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                },
                {
                    "id": 5,
                    "user": {
                        "id": 5,
                        "username": "warehouse",
                        "email": "warehouse@example.com",
                        "first_name": "Warehouse",
                        "last_name": "Manager",
                        "is_active": True
                    },
                    "company_name": "C Supplies Inc.",
                    "code": "SUP-290",
                    "business_type": "Manufacturing",
                    "tax_id": "TAX10636",
                    "compliance_score": 5.0,
                    "active": True,
                    "created_at": "2025-05-05T11:20:45.169505Z",
                    "updated_at": "2025-05-05T11:20:45.169505Z"
                }
            ]
            
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/suppliers/",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching all suppliers: {str(e)}")
            return []
            
    def test_connection(self):
        """
        Test connection to the Auth Service
        Returns True if connection is successful, False otherwise
        """
        if self.use_dummy_data:
            # Always return success when using dummy data
            return True
            
        try:
            # Try to connect to the base URL with auth headers for auth-required endpoints
            response = requests.get(
                f"{self.base_url}/api/v1/health-check/",
                headers=self.headers,  # Include headers for authenticated health check
                timeout=5  # Short timeout for health check
            )
            
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False