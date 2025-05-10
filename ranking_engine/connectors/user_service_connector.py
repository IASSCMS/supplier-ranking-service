import requests
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

class UserServiceConnector:
    """Connector to fetch supplier data from the User Service"""
    
    def __init__(self):
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
        
        logger.info(f"Initialized UserServiceConnector with base URL: {self.base_url}")
        
    def get_active_suppliers(self):
        """Fetch all active suppliers from User Service"""
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
        try:
            url = f"{self.base_url}/api/v1/suppliers/{supplier_id}/info/"
            logger.debug(f"Making request to: {url}")
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            # Log more details for debugging
            if response.status_code != 200:
                logger.error(f"API response error: Status {response.status_code}, Content: {response.text[:200]}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching supplier info {supplier_id}: {str(e)}")
            # For debugging, log more details
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text[:200]}")
            return None
            
    def test_connection(self):
        """
        Test connection to the Auth Service
        Returns True if connection is successful, False otherwise
        """
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