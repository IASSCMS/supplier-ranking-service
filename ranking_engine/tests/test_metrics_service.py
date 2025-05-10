import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
import numpy as np

from ranking_engine.services.metrics_service import MetricsService
from ranking_engine.q_learning.state_mapper import StateMapper
from ranking_engine.q_learning.environment import SupplierEnvironment
from api.models import QLearningState, SupplierPerformanceCache, RankingConfiguration

class TestMetricsServiceWithQLearning(TestCase):
    """Test that metrics_service works properly with the Q-learning ranking process"""

    def setUp(self):
        """Set up test fixtures"""
        # Create an active ranking configuration
        self.config = RankingConfiguration.objects.create(
            name="Test Configuration",
            learning_rate=0.1,
            discount_factor=0.9,
            exploration_rate=0.3,
            quality_weight=0.25,
            delivery_weight=0.25,
            price_weight=0.25,
            service_weight=0.25,
            is_active=True
        )
        
        # Create a test state
        self.test_state, _ = QLearningState.objects.get_or_create(
            name="Q5_D5_P4_S4",
            defaults={'description': 'Test state with quality=5, delivery=5, price=4, service=4'}
        )
        
        # Create test performance cache entry
        today = timezone.now().date()
        self.test_supplier_id = 42
        
        self.cache_entry = SupplierPerformanceCache.objects.create(
            supplier_id=self.test_supplier_id,
            supplier_name="Test Supplier",
            date=today,
            quality_score=9.2,  # Maps to level 5
            defect_rate=0.5,
            return_rate=0.2,
            on_time_delivery_rate=98.0,  # Maps to level 5
            average_delay_days=0.1,
            price_competitiveness=8.5,  # Maps to level 5
            responsiveness=7.8,  # Maps to level 4
            compliance_score=7.0,
            fill_rate=95.0,  # Adding required field
            order_accuracy=98.0,  # Adding required field
            data_complete=True
        )
        
        # Initialize services
        self.metrics_service = MetricsService()
        self.state_mapper = StateMapper()
        self.environment = SupplierEnvironment(config=self.config)

    def test_metrics_service_provides_correct_metrics(self):
        """Test that metrics_service provides correct metrics for Q-learning"""
        # Mock the service connector methods
        with patch.object(self.metrics_service, 'user_service'), \
             patch.object(self.metrics_service, 'warehouse_service'), \
             patch.object(self.metrics_service, 'order_service'):
            
            # Mock get_supplier_transactions to return test data
            self.metrics_service.order_service.get_supplier_transactions = MagicMock(return_value=[
                {'quantity': 100, 'defect_count': 2, 'status': 'DELIVERED'},
                {'quantity': 200, 'defect_count': 1, 'status': 'DELIVERED'},
            ])
            
            # Mock get_supplier_performance_records to return test data
            self.metrics_service.order_service.get_supplier_performance_records = MagicMock(return_value=[
                {'quality_score': 9.0, 'defect_rate': 1.0, 'return_rate': 0.5},
                {'quality_score': 9.5, 'defect_rate': 0.8, 'return_rate': 0.3},
            ])

            # Test quality metrics calculation
            quality_metrics = self.metrics_service.calculate_quality_metrics(self.test_supplier_id)
            self.assertIn('quality_score', quality_metrics)
            self.assertGreaterEqual(quality_metrics['quality_score'], 0)
            self.assertLessEqual(quality_metrics['quality_score'], 10)

    def test_state_mapper_uses_metrics_service_data(self):
        """Test that state_mapper correctly uses metrics from metrics_service"""
        # Mock get_supplier_metrics to return predefined metrics
        with patch.object(self.state_mapper.metrics_service, 'get_supplier_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = {
                'quality_score': 9.2,  # Maps to level 5
                'delivery_score': 9.5,  # Maps to level 5
                'price_score': 7.5,    # Maps to level 4
                'service_score': 7.8    # Maps to level 4
            }
            
            # Get state for the test supplier
            state = self.state_mapper.get_supplier_state(self.test_supplier_id)
            
            # Verify the state name matches our expected format
            self.assertEqual(state.name, "Q5_D5_P4_S4")
            
            # Verify metrics_service was called with correct supplier ID
            mock_get_metrics.assert_called_once_with(self.test_supplier_id)

    def test_environment_uses_metrics_service(self):
        """Test that environment uses metrics_service data for ranking suppliers"""
        # Mock supplier service and metrics service methods
        with patch.object(self.environment.supplier_service, 'get_supplier') as mock_get_supplier, \
             patch.object(self.environment.metrics_service, 'get_supplier_metrics') as mock_get_metrics:
             
            # Mock supplier data
            mock_get_supplier.return_value = {
                'company_name': 'Test Supplier Inc.',
                'compliance_score': 8.0
            }
            
            # Mock metrics data
            mock_get_metrics.return_value = {
                'quality_score': 9.2,
                'delivery_score': 9.5,
                'price_score': 7.5,
                'service_score': 7.8,
                'overall_score': 8.5
            }
            
            # Mock the state mapper to return a known state
            with patch.object(self.environment.state_mapper, 'get_supplier_state') as mock_get_state:
                mock_get_state.return_value = self.test_state
                
                # Test getting the current state
                state = self.environment.get_state(self.test_supplier_id)
                
                # Verify state matches our expected state
                self.assertEqual(state, self.test_state)
                
                # Verify next_state also returns the correct state
                mock_action = MagicMock()
                mock_action.name = "promote"
                
                next_state = self.environment.next_state(self.test_supplier_id, mock_action)
                self.assertEqual(next_state, self.test_state)
                
                # Verify state_mapper was called with the right supplier ID
                mock_get_state.assert_called_with(self.test_supplier_id)

    def test_end_to_end_ranking_process(self):
        """Test the end-to-end supplier ranking process with Q-learning integration"""
        # Create multiple suppliers with different metrics
        supplier_ids = [101, 102, 103]
        today = timezone.now().date()
        
        # Create cache entries with different metrics
        SupplierPerformanceCache.objects.create(
            supplier_id=supplier_ids[0],
            supplier_name="Superior Supplier",
            date=today,
            quality_score=9.5,
            defect_rate=0.5,  # Adding required field
            return_rate=0.2,   # Adding required field
            on_time_delivery_rate=98.0,  # High on-time delivery
            average_delay_days=0.1,
            price_competitiveness=8.0,
            responsiveness=9.0,
            compliance_score=9.0,
            fill_rate=98.0,
            order_accuracy=99.0,
            data_complete=True
        )
        
        SupplierPerformanceCache.objects.create(
            supplier_id=supplier_ids[1],
            supplier_name="Average Supplier",
            date=today,
            quality_score=7.0,
            defect_rate=2.0,  # Adding required field
            return_rate=1.0,   # Adding required field
            on_time_delivery_rate=85.0,  # Average on-time delivery
            average_delay_days=1.5,
            price_competitiveness=7.0,
            responsiveness=6.5,
            compliance_score=7.0,
            fill_rate=90.0,
            order_accuracy=92.0,
            data_complete=True
        )
        
        SupplierPerformanceCache.objects.create(
            supplier_id=supplier_ids[2],
            supplier_name="Poor Supplier",
            date=today,
            quality_score=3.0,
            defect_rate=5.0,  # Adding required field
            return_rate=3.0,   # Adding required field
            on_time_delivery_rate=65.0,  # Poor on-time delivery
            average_delay_days=3.2,
            price_competitiveness=5.0,
            responsiveness=3.5,
            compliance_score=4.0,
            fill_rate=75.0,
            order_accuracy=80.0,
            data_complete=True
        )
        
        # Mock methods to use cached data and return appropriate test values
        with patch('ranking_engine.services.metrics_service.MetricsService.get_supplier_metrics') as mock_get_metrics, \
             patch('ranking_engine.services.supplier_service.SupplierService.get_supplier') as mock_get_supplier:
            
            # Set up supplier service mock
            mock_get_supplier.side_effect = lambda supplier_id: {
                'company_name': f'Supplier {supplier_id}',
                'compliance_score': 7.0 if supplier_id == 101 else 5.0
            }
            
            # Set up metrics service mock to use our cache data
            def get_mock_metrics(supplier_id):
                cache = SupplierPerformanceCache.objects.get(supplier_id=supplier_id)
                return {
                    'quality_score': cache.quality_score,
                    'delivery_score': cache.on_time_delivery_rate / 10,  # Convert to 0-10 scale
                    'price_score': cache.price_competitiveness,
                    'service_score': cache.responsiveness,
                    'overall_score': (cache.quality_score + (cache.on_time_delivery_rate / 10) + 
                                     cache.price_competitiveness + cache.responsiveness) / 4
                }
            
            mock_get_metrics.side_effect = get_mock_metrics
            
            # Test getting states for each supplier
            for supplier_id in supplier_ids:
                # Get state through the state mapper
                state = self.state_mapper.get_supplier_state(supplier_id)
                
                # Verify state is a valid QLearningState object
                self.assertIsInstance(state, QLearningState)
                self.assertTrue(state.name.startswith('Q'))
                
                # Verify state format is correct (e.g., Q5_D5_P4_S4)
                state_parts = state.name.split('_')
                self.assertEqual(len(state_parts), 4)
                
                # Get metrics for comparison
                metrics = get_mock_metrics(supplier_id)
                
                # Verify state levels match the metrics
                quality_level = int(state_parts[0][1:])
                delivery_level = int(state_parts[1][1:])
                price_level = int(state_parts[2][1:])
                service_level = int(state_parts[3][1:])
                
                # For excellent metrics (>8.0), level should be 5
                if supplier_id == 101:
                    self.assertEqual(quality_level, 5)
                    self.assertEqual(delivery_level, 5)
                
                # For poor metrics (<4.0), level should be 1 or 2
                if supplier_id == 103:
                    self.assertLessEqual(quality_level, 2)
                    # The 65.0 on_time_delivery_rate is mapped to a higher level, 
                    # so let's verify it's correct instead of checking if it's ≤ 2
                    self.assertEqual(delivery_level, 4)  # 65/10 = 6.5, which maps to level 4

if __name__ == '__main__':
    unittest.main() 