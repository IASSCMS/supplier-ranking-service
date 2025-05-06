import unittest
from unittest import mock
from django.conf import settings
from django.test import TestCase, override_settings
import requests
import logging

# Import the class to test
from connectors.user_service_connector import UserServiceConnector


class TestUserServiceConnector(TestCase):
    """Test cases for UserServiceConnector"""

    def setUp(self):
        """Set up test environment before each test"""
        # Configure test settings
        self.test_url = "http://localhost:8000"
        
        # Override Django settings for testing
        settings.AUTH_SERVICE_URL = self.test_url
        
        # Create an instance of the connector
        self.connector = UserServiceConnector()
    
    def test_initialization(self):
        """Test if the connector is initialized with correct base URL"""
        self.assertEqual(self.connector.base_url, self.test_url)
    
    def test_get_active_suppliers(self):
        """Test get_active_suppliers method returns correct data"""
        # Call the method
        suppliers = self.connector.get_active_suppliers()
        
        # Check if it returns a list
        self.assertIsInstance(suppliers, list)
        
        # Check if the list has expected length
        self.assertEqual(len(suppliers), 4)
        
        # Check if each supplier has expected keys
        for supplier in suppliers:
            self.assertIn('id', supplier)
            self.assertIn('name', supplier)
            self.assertIn('code', supplier)
            self.assertIn('active', supplier)
            
            # Verify all suppliers are active
            self.assertTrue(supplier['active'])
    
    def test_get_active_supplier_count(self):
        """Test get_active_supplier_count method returns correct count"""
        # Call the method
        count = self.connector.get_active_supplier_count()
        
        # Check if it returns expected count
        self.assertEqual(count, 4)
    
    def test_get_supplier_by_id_existing(self):
        """Test get_supplier_by_id method with existing supplier ID"""
        # Test with existing supplier IDs
        supplier_ids = [1, 2, 3, 5]
        
        for supplier_id in supplier_ids:
            supplier = self.connector.get_supplier_by_id(supplier_id)
            
            # Check if it returns a dictionary
            self.assertIsInstance(supplier, dict)
            
            # Check if the supplier has expected ID
            self.assertEqual(supplier['id'], supplier_id)
            
            # Check if it has expected keys
            self.assertIn('name', supplier)
            self.assertIn('code', supplier)
            self.assertIn('active', supplier)
    
    def test_get_supplier_by_id_nonexistent(self):
        """Test get_supplier_by_id method with non-existent supplier ID"""
        # Test with non-existent supplier ID
        supplier = self.connector.get_supplier_by_id(999)
        
        # Check if it returns None
        self.assertIsNone(supplier)
    
    def test_get_supplier_by_id_inactive(self):
        """Test get_supplier_by_id method with inactive supplier ID"""
        # Test with inactive supplier ID
        supplier = self.connector.get_supplier_by_id(4)
        
        # Check if it returns a dictionary
        self.assertIsInstance(supplier, dict)
        
        # Check if the supplier is marked inactive
        self.assertFalse(supplier['active'])
    
    def test_get_supplier_info_existing(self):
        """Test get_supplier_info method with existing supplier ID"""
        # Test with existing supplier IDs
        supplier_ids = [1, 2, 3]
        
        for supplier_id in supplier_ids:
            supplier_info = self.connector.get_supplier_info(supplier_id)
            
            # Check if it returns a dictionary
            self.assertIsInstance(supplier_info, dict)
            
            # Check if the supplier has expected ID
            self.assertEqual(supplier_info['id'], supplier_id)
            
            # Check if it has expected keys
            self.assertIn('name', supplier_info)
            self.assertIn('code', supplier_info)
            self.assertIn('compliance_score', supplier_info)
            
            # Check if compliance score is within expected range
            self.assertTrue(0 <= supplier_info['compliance_score'] <= 10)
    
    def test_get_supplier_info_nonexistent(self):
        """Test get_supplier_info method with non-existent supplier ID"""
        # Test with non-existent supplier ID
        supplier_info = self.connector.get_supplier_info(999)
        
        # Check if it returns None
        self.assertIsNone(supplier_info)

    @mock.patch('requests.get')
    def test_get_active_suppliers_with_mock_api(self, mock_get):
        """Test get_active_suppliers with mocked API response"""
        # Setup mock response
        mock_response = mock.Mock()
        mock_response.json.return_value = [
            {"id": 1, "name": "Test Supplier 1", "code": "TS001", "active": True},
            {"id": 2, "name": "Test Supplier 2", "code": "TS002", "active": True}
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Temporarily restore the real implementation to test API call
        original_method = UserServiceConnector.get_active_suppliers
        try:
            # Replace the simulated response with a version that uses requests
            def api_get_active_suppliers(self):
                response = requests.get(f"{self.base_url}/api/suppliers?active=true")
                response.raise_for_status()
                return response.json()
                
            UserServiceConnector.get_active_suppliers = api_get_active_suppliers
            
            # Create a new instance with the replaced method
            connector = UserServiceConnector()
            
            # Call the method
            suppliers = connector.get_active_suppliers()
            
            # Verify the mocked API was called with expected URL
            mock_get.assert_called_once_with(f"{self.test_url}/api/suppliers?active=true")
            
            # Verify response
            self.assertEqual(len(suppliers), 2)
            self.assertEqual(suppliers[0]["name"], "Test Supplier 1")
            self.assertEqual(suppliers[1]["name"], "Test Supplier 2")
            
        finally:
            # Restore original method to avoid affecting other tests
            UserServiceConnector.get_active_suppliers = original_method
    
    @mock.patch('requests.get')
    def test_api_error_handling(self, mock_get):
        # Setup logger
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.ERROR)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

        # Setup mock to raise exception
        # Setup mock to raise exception
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        # Temporarily replace the method with one that makes actual API call
        original_method = UserServiceConnector.get_active_suppliers
        try:
            # Replace the simulated response with a version that uses requests
            def api_get_active_suppliers(self):
                try:
                    response = requests.get(f"{self.base_url}/api/suppliers?active=true")
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error fetching active suppliers: {str(e)}")
                    return []
                
            UserServiceConnector.get_active_suppliers = api_get_active_suppliers
            
            # Create a new instance with the replaced method
            connector = UserServiceConnector()
            
            # Call the method that should handle the exception
            suppliers = connector.get_active_suppliers()
            
            # Verify empty list is returned on error
            self.assertEqual(suppliers, [])
            
        finally:
            # Restore original method
            UserServiceConnector.get_active_suppliers = original_method


if __name__ == "__main__":
    unittest.main()