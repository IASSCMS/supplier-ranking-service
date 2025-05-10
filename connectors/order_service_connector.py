"""
Connector for the Order Service that handles transaction data.
"""

import requests
import logging
import os
from django.conf import settings
from datetime import datetime, date, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

class OrderServiceConnector:
    """Connector to fetch order and transaction data from the Order Service"""
    
    def __init__(self, use_dummy_data=True):
        """Initialize connector with base URL and auth credentials from settings"""
        # Use environment variable first, then settings
        self.base_url = os.environ.get('ORDER_SERVICE_URL', 'http://localhost:8002')
        
        # Fix URL if running in Docker but using localhost
        if 'localhost' in self.base_url and os.environ.get('DOCKER_ENV', 'False') == 'True':
            self.base_url = os.environ.get('ORDER_SERVICE_URL', 'http://localhost:8002')
            
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
        
        logger.info(f"Initialized OrderServiceConnector with base URL: {self.base_url}")
    
    def _create_dummy_data(self):
        """Create dummy data for testing"""
        today = date.today()
        
        # Generate transaction history for suppliers
        self.dummy_transactions = {
            3: [  # Supplier A transactions
                {
                    "id": 101,
                    "supplier_id": 3,
                    "product_id": 1,
                    "order_id": "ORD-1001",
                    "quantity": 100,
                    "unit_price": 9.50,
                    "total_price": 950.00,
                    "status": "DELIVERED",
                    "expected_delivery_date": (today - timedelta(days=30)).isoformat(),
                    "actual_delivery_date": (today - timedelta(days=29)).isoformat(),
                    "defect_count": 3,
                    "created_at": (today - timedelta(days=45)).isoformat()
                },
                {
                    "id": 102,
                    "supplier_id": 3,
                    "product_id": 2,
                    "order_id": "ORD-1002",
                    "quantity": 50,
                    "unit_price": 14.75,
                    "total_price": 737.50,
                    "status": "DELIVERED",
                    "expected_delivery_date": (today - timedelta(days=20)).isoformat(),
                    "actual_delivery_date": (today - timedelta(days=21)).isoformat(),
                    "defect_count": 0,
                    "created_at": (today - timedelta(days=30)).isoformat()
                },
                {
                    "id": 103,
                    "supplier_id": 3,
                    "product_id": 1,
                    "order_id": "ORD-1003",
                    "quantity": 75,
                    "unit_price": 9.50,
                    "total_price": 712.50,
                    "status": "RETURNED",
                    "expected_delivery_date": (today - timedelta(days=15)).isoformat(),
                    "actual_delivery_date": (today - timedelta(days=16)).isoformat(),
                    "defect_count": 20,
                    "created_at": (today - timedelta(days=25)).isoformat()
                }
            ],
            4: [  # Supplier B transactions
                {
                    "id": 201,
                    "supplier_id": 4,
                    "product_id": 1,
                    "order_id": "ORD-2001",
                    "quantity": 80,
                    "unit_price": 9.80,
                    "total_price": 784.00,
                    "status": "DELIVERED",
                    "expected_delivery_date": (today - timedelta(days=25)).isoformat(),
                    "actual_delivery_date": (today - timedelta(days=22)).isoformat(),
                    "defect_count": 1,
                    "created_at": (today - timedelta(days=35)).isoformat()
                },
                {
                    "id": 202,
                    "supplier_id": 4,
                    "product_id": 1,
                    "order_id": "ORD-2002",
                    "quantity": 60,
                    "unit_price": 9.80,
                    "total_price": 588.00,
                    "status": "DELIVERED",
                    "expected_delivery_date": (today - timedelta(days=10)).isoformat(),
                    "actual_delivery_date": (today - timedelta(days=10)).isoformat(),
                    "defect_count": 0,
                    "created_at": (today - timedelta(days=20)).isoformat()
                }
            ],
            5: [  # Supplier C transactions
                {
                    "id": 301,
                    "supplier_id": 5,
                    "product_id": 2,
                    "order_id": "ORD-3001",
                    "quantity": 40,
                    "unit_price": 14.50,
                    "total_price": 580.00,
                    "status": "DELIVERED",
                    "expected_delivery_date": (today - timedelta(days=15)).isoformat(),
                    "actual_delivery_date": (today - timedelta(days=16)).isoformat(),
                    "defect_count": 2,
                    "created_at": (today - timedelta(days=25)).isoformat()
                },
                {
                    "id": 302,
                    "supplier_id": 5,
                    "product_id": 3,
                    "order_id": "ORD-3002",
                    "quantity": 200,
                    "unit_price": 4.90,
                    "total_price": 980.00,
                    "status": "DELIVERED",
                    "expected_delivery_date": (today - timedelta(days=7)).isoformat(),
                    "actual_delivery_date": (today - timedelta(days=5)).isoformat(),
                    "defect_count": 0,
                    "created_at": (today - timedelta(days=15)).isoformat()
                }
            ]
        }
        
        # Generate performance records
        self.dummy_performance_records = {
            3: [  # Supplier A performance
                {
                    "supplier_id": 3,
                    "date": (today - timedelta(days=30)).isoformat(),
                    "quality_score": 8.5,
                    "defect_rate": 3.0,
                    "return_rate": 1.0,
                    "on_time_delivery_rate": 95.0,
                    "price_competitiveness": 8.0,
                    "responsiveness": 9.0,
                    "fill_rate": 98.0,
                    "order_accuracy": 97.0
                },
                {
                    "supplier_id": 3,
                    "date": (today - timedelta(days=15)).isoformat(),
                    "quality_score": 7.8,
                    "defect_rate": 5.0,
                    "return_rate": 5.0,
                    "on_time_delivery_rate": 90.0,
                    "price_competitiveness": 8.0,
                    "responsiveness": 8.5,
                    "fill_rate": 96.0,
                    "order_accuracy": 95.0
                }
            ],
            4: [  # Supplier B performance
                {
                    "supplier_id": 4,
                    "date": (today - timedelta(days=30)).isoformat(),
                    "quality_score": 9.0,
                    "defect_rate": 1.5,
                    "return_rate": 0.5,
                    "on_time_delivery_rate": 97.0,
                    "price_competitiveness": 7.5,
                    "responsiveness": 8.0,
                    "fill_rate": 99.0,
                    "order_accuracy": 98.0
                },
                {
                    "supplier_id": 4,
                    "date": (today - timedelta(days=15)).isoformat(),
                    "quality_score": 9.2,
                    "defect_rate": 1.0,
                    "return_rate": 0.0,
                    "on_time_delivery_rate": 98.0,
                    "price_competitiveness": 7.5,
                    "responsiveness": 8.0,
                    "fill_rate": 99.0,
                    "order_accuracy": 99.0
                }
            ],
            5: [  # Supplier C performance
                {
                    "supplier_id": 5,
                    "date": (today - timedelta(days=30)).isoformat(),
                    "quality_score": 9.5,
                    "defect_rate": 1.0,
                    "return_rate": 0.0,
                    "on_time_delivery_rate": 98.0,
                    "price_competitiveness": 8.5,
                    "responsiveness": 9.0,
                    "fill_rate": 99.5,
                    "order_accuracy": 99.0
                },
                {
                    "supplier_id": 5,
                    "date": (today - timedelta(days=15)).isoformat(),
                    "quality_score": 9.6,
                    "defect_rate": 0.5,
                    "return_rate": 0.0,
                    "on_time_delivery_rate": 99.0,
                    "price_competitiveness": 8.5,
                    "responsiveness": 9.0,
                    "fill_rate": 99.5,
                    "order_accuracy": 99.5
                }
            ]
        }
        
        # Generate category performance data
        self.dummy_category_performance = {
            3: {  # Supplier A
                "Widgets": {
                    "quality_score": 8.2,
                    "on_time_delivery_rate": 92.5,
                    "price_competitiveness": 8.0
                },
                "Components": {
                    "quality_score": 8.5,
                    "on_time_delivery_rate": 95.0,
                    "price_competitiveness": 7.8
                }
            },
            4: {  # Supplier B
                "Widgets": {
                    "quality_score": 9.1,
                    "on_time_delivery_rate": 97.5,
                    "price_competitiveness": 7.5
                }
            },
            5: {  # Supplier C
                "Components": {
                    "quality_score": 9.6,
                    "on_time_delivery_rate": 98.5,
                    "price_competitiveness": 8.5
                },
                "Raw Materials": {
                    "quality_score": 9.4,
                    "on_time_delivery_rate": 97.0,
                    "price_competitiveness": 8.6
                }
            }
        }
    
    def get_supplier_transactions(self, supplier_id, start_date=None, status=None, has_delivery_date=False):
        """
        Get transactions for a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            start_date (date or datetime, optional): Start date for filtering transactions
            status (list, optional): List of status values to filter by
            has_delivery_date (bool, optional): If True, only return transactions with delivery dates
            
        Returns:
            list: List of transaction dictionaries
        """
        if self.use_dummy_data:
            # Get transactions for this supplier
            supplier_transactions = self.dummy_transactions.get(supplier_id, [])
            
            # Apply filters
            filtered_transactions = []
            for tx in supplier_transactions:
                # Filter by start date
                if start_date:
                    # Make sure we convert to a datetime for comparison
                    tx_date = datetime.fromisoformat(tx['created_at'].replace('Z', '+00:00'))
                    
                    # Convert start_date to datetime if it's a date object
                    if isinstance(start_date, date) and not isinstance(start_date, datetime):
                        start_date_dt = datetime.combine(start_date, datetime.min.time())
                    else:
                        start_date_dt = start_date
                    
                    # Now handle timezone awareness
                    if hasattr(start_date_dt, 'tzinfo') and start_date_dt.tzinfo is not None and tx_date.tzinfo is None:
                        # Make tx_date timezone-aware if it isn't already
                        tx_date = timezone.make_aware(tx_date)
                    elif hasattr(start_date_dt, 'tzinfo') and start_date_dt.tzinfo is None and tx_date.tzinfo is not None:
                        # Make start_date timezone-aware if it isn't already
                        start_date_dt = timezone.make_aware(start_date_dt)
                    
                    if tx_date < start_date_dt:
                        continue
                
                # Filter by status
                if status and tx['status'] not in status:
                    continue
                
                # Filter by has_delivery_date
                if has_delivery_date and (not tx.get('expected_delivery_date') or not tx.get('actual_delivery_date')):
                    continue
                
                filtered_transactions.append(tx)
            
            return filtered_transactions
        
        try:
            params = {'supplier_id': supplier_id}
            
            if start_date:
                params['start_date'] = start_date.isoformat()
            
            if status:
                params['status'] = ','.join(status)
            
            if has_delivery_date:
                params['has_delivery_date'] = 'true'
            
            response = requests.get(
                f"{self.base_url}/api/v1/transactions/",
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching transactions for supplier {supplier_id}: {str(e)}")
            return []
    
    def get_supplier_performance_records(self, supplier_id, start_date=None):
        """
        Get performance records for a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            start_date (date or datetime, optional): Start date for filtering records
            
        Returns:
            list: List of performance record dictionaries
        """
        if self.use_dummy_data:
            # Get performance records for this supplier
            supplier_records = self.dummy_performance_records.get(supplier_id, [])
            
            # Apply start_date filter if provided
            if start_date:
                filtered_records = []
                for record in supplier_records:
                    # Make sure we convert to a datetime for comparison
                    record_date = datetime.fromisoformat(record['date'].replace('Z', '+00:00'))
                    
                    # Convert start_date to datetime if it's a date object
                    if isinstance(start_date, date) and not isinstance(start_date, datetime):
                        start_date_dt = datetime.combine(start_date, datetime.min.time())
                    else:
                        start_date_dt = start_date
                    
                    # Handle timezone awareness for comparison
                    if hasattr(start_date_dt, 'tzinfo') and start_date_dt.tzinfo is not None and record_date.tzinfo is None:
                        # Make record_date timezone-aware
                        record_date = timezone.make_aware(record_date)
                    elif hasattr(start_date_dt, 'tzinfo') and start_date_dt.tzinfo is None and record_date.tzinfo is not None:
                        # Make start_date timezone-aware
                        start_date_dt = timezone.make_aware(start_date_dt)
                        
                    if record_date >= start_date_dt:
                        filtered_records.append(record)
                return filtered_records
            
            return supplier_records
        
        try:
            params = {'supplier_id': supplier_id}
            
            if start_date:
                params['start_date'] = start_date.isoformat()
            
            response = requests.get(
                f"{self.base_url}/api/v1/supplier-performance/",
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching performance records for supplier {supplier_id}: {str(e)}")
            return []
    
    def get_supplier_performance(self, supplier_id, start_date=None):
        """
        Get aggregated performance data for a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            start_date (datetime, optional): Start date for filtering data
            
        Returns:
            dict: Dictionary containing aggregated performance metrics
        """
        # This function typically calls get_supplier_performance_records and aggregates the data
        # For simplicity with dummy data, we'll just return the most recent record
        
        records = self.get_supplier_performance_records(supplier_id, start_date)
        
        if not records:
            return {
                'quality_score': 8.0,
                'defect_rate': 2.0,
                'return_rate': 1.0,
                'on_time_delivery_rate': 95.0,
                'price_competitiveness': 7.5,
                'responsiveness': 8.0,
                'fill_rate': 97.0,
                'order_accuracy': 98.0
            }
        
        # Sort by date (most recent first) and return the first one
        sorted_records = sorted(records, key=lambda r: r['date'], reverse=True)
        return sorted_records[0]
    
    def get_supplier_category_performance(self, supplier_id):
        """
        Get performance data grouped by product category for a specific supplier
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            dict: Dictionary containing performance metrics by category
        """
        if self.use_dummy_data:
            return self.dummy_category_performance.get(supplier_id, {})
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/supplier-category-performance/{supplier_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching category performance for supplier {supplier_id}: {str(e)}")
            return {}
    
    def test_connection(self):
        """
        Test connection to the Order Service
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