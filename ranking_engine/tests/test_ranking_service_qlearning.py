import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta

from ranking_engine.services.ranking_service import RankingService
from ranking_engine.q_learning.state_mapper import StateMapper
from ranking_engine.q_learning.environment import SupplierEnvironment
from ranking_engine.q_learning.agent import SupplierRankingAgent
from api.models import (
    QLearningState, 
    QLearningAction, 
    QTableEntry,
    SupplierRanking, 
    SupplierPerformanceCache, 
    RankingConfiguration,
    RankingEvent
)

class TestRankingServiceQLearning(TestCase):
    """Test that RankingService correctly uses Q-learning for supplier ranking"""

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
        
        # Create test states
        self.excellent_state, _ = QLearningState.objects.get_or_create(
            name="Q5_D5_P5_S5",
            defaults={'description': 'Excellent state'}
        )
        
        self.good_state, _ = QLearningState.objects.get_or_create(
            name="Q4_D4_P4_S4",
            defaults={'description': 'Good state'}
        )
        
        self.average_state, _ = QLearningState.objects.get_or_create(
            name="Q3_D3_P3_S3",
            defaults={'description': 'Average state'}
        )
        
        self.poor_state, _ = QLearningState.objects.get_or_create(
            name="Q2_D2_P2_S2",
            defaults={'description': 'Poor state'}
        )
        
        # Create test actions
        self.rank_tier_1 = QLearningAction.objects.create(
            name="RANK_TIER_1",
            description="Rank supplier as Tier 1 (Preferred)"
        )
        
        self.rank_tier_2 = QLearningAction.objects.create(
            name="RANK_TIER_2",
            description="Rank supplier as Tier 2 (Approved)"
        )
        
        self.rank_tier_3 = QLearningAction.objects.create(
            name="RANK_TIER_3",
            description="Rank supplier as Tier 3 (Conditional)"
        )
        
        # Create some Q-table entries directly using QTableEntry
        # Excellent state prefers Tier 1
        QTableEntry.objects.create(
            state=self.excellent_state,
            action=self.rank_tier_1,
            q_value=9.0
        )
        
        QTableEntry.objects.create(
            state=self.excellent_state,
            action=self.rank_tier_2,
            q_value=5.0
        )
        
        # Good state prefers Tier 2
        QTableEntry.objects.create(
            state=self.good_state,
            action=self.rank_tier_1,
            q_value=4.0
        )
        
        QTableEntry.objects.create(
            state=self.good_state,
            action=self.rank_tier_2,
            q_value=8.0
        )
        
        # Average state prefers Tier 3
        QTableEntry.objects.create(
            state=self.average_state,
            action=self.rank_tier_2,
            q_value=3.0
        )
        
        QTableEntry.objects.create(
            state=self.average_state,
            action=self.rank_tier_3,
            q_value=7.0
        )
        
        # Create test supplier data
        self.supplier_ids = [201, 202, 203]
        today = timezone.now().date()
        
        # Create performance cache entries for different suppliers
        SupplierPerformanceCache.objects.create(
            supplier_id=self.supplier_ids[0],
            supplier_name="Excellent Supplier",
            date=today,
            quality_score=9.5,
            defect_rate=0.5,
            return_rate=0.2,
            on_time_delivery_rate=95.0,
            average_delay_days=0.1,
            price_competitiveness=9.0,
            responsiveness=9.0,
            compliance_score=9.0,
            fill_rate=98.0,
            order_accuracy=99.0,
            data_complete=True
        )
        
        SupplierPerformanceCache.objects.create(
            supplier_id=self.supplier_ids[1],
            supplier_name="Good Supplier",
            date=today,
            quality_score=7.5,
            defect_rate=1.8,
            return_rate=1.2,
            on_time_delivery_rate=85.0,
            average_delay_days=1.0,
            price_competitiveness=7.5,
            responsiveness=7.5,
            compliance_score=7.5,
            fill_rate=90.0,
            order_accuracy=92.0,
            data_complete=True
        )
        
        SupplierPerformanceCache.objects.create(
            supplier_id=self.supplier_ids[2],
            supplier_name="Average Supplier",
            date=today,
            quality_score=5.5,
            defect_rate=3.0,
            return_rate=2.5,
            on_time_delivery_rate=75.0,
            average_delay_days=2.0,
            price_competitiveness=5.5,
            responsiveness=5.5,
            compliance_score=5.5,
            fill_rate=85.0,
            order_accuracy=88.0,
            data_complete=True
        )
        
        # Initialize services
        self.ranking_service = RankingService()

    def test_ranking_service_uses_q_learning(self):
        """Test that RankingService uses Q-learning to rank suppliers"""
        # Mock necessary methods
        with patch('ranking_engine.services.metrics_service.MetricsService.get_supplier_metrics') as mock_get_metrics, \
             patch('ranking_engine.services.supplier_service.SupplierService.get_supplier') as mock_get_supplier, \
             patch('ranking_engine.q_learning.state_mapper.StateMapper.get_supplier_state') as mock_get_state, \
             patch('ranking_engine.q_learning.agent.SupplierRankingAgent.select_action') as mock_select_action, \
             patch('connectors.user_service_connector.UserServiceConnector.get_active_suppliers') as mock_get_active_suppliers, \
             patch('connectors.user_service_connector.UserServiceConnector.get_supplier_by_id') as mock_get_supplier_by_id:
            
            # Mock active suppliers list
            mock_get_active_suppliers.return_value = [
                {'user': {'id': self.supplier_ids[0]}},
                {'user': {'id': self.supplier_ids[1]}},
                {'user': {'id': self.supplier_ids[2]}}
            ]
            
            # Mock supplier_by_id to return supplier data
            mock_get_supplier_by_id.side_effect = lambda supplier_id: {
                'company_name': f'Supplier {supplier_id}',
                'compliance_score': 8.0 if supplier_id == self.supplier_ids[0] else 7.0
            }
            
            # Set up supplier service mock
            mock_get_supplier.side_effect = lambda supplier_id: {
                'company_name': f'Supplier {supplier_id}',
                'compliance_score': 7.0
            }
            
            # Set up metrics service mock
            def mock_metrics_func(supplier_id):
                cache = SupplierPerformanceCache.objects.get(supplier_id=supplier_id)
                return {
                    'quality_score': cache.quality_score,
                    'delivery_score': cache.on_time_delivery_rate / 10,  # Convert to 0-10 scale
                    'price_score': cache.price_competitiveness,
                    'service_score': cache.responsiveness,
                    'overall_score': (cache.quality_score + (cache.on_time_delivery_rate / 10) + 
                                    cache.price_competitiveness + cache.responsiveness) / 4
                }
            
            mock_get_metrics.side_effect = mock_metrics_func
            
            # Set up state mapper mock
            mock_get_state.side_effect = lambda supplier_id: (
                self.excellent_state if supplier_id == self.supplier_ids[0] else (
                    self.good_state if supplier_id == self.supplier_ids[1] else
                    self.average_state
                )
            )
            
            # Set up agent mock - use *args, **kwargs to handle any parameter signature
            mock_select_action.side_effect = lambda state, *args, **kwargs: (
                self.rank_tier_1 if state == self.excellent_state else (
                    self.rank_tier_2 if state == self.good_state else 
                    self.rank_tier_3
                )
            )
            
            # Call generate_rankings
            rankings = self.ranking_service.generate_rankings()
            
            # Verify rankings were created
            self.assertEqual(len(rankings), 3)
            
            # Verify ranking order (by rank field)
            ranked_supplier_ids = [ranking.supplier_id for ranking in rankings]
            self.assertEqual(ranked_supplier_ids[0], self.supplier_ids[0])  # Excellent supplier should be ranked 1st
            self.assertEqual(ranked_supplier_ids[1], self.supplier_ids[1])  # Good supplier should be ranked 2nd
            self.assertEqual(ranked_supplier_ids[2], self.supplier_ids[2])  # Average supplier should be ranked 3rd
            
            # Verify that state mapper and agent were called correctly
            mock_get_state.assert_any_call(self.supplier_ids[0])
            mock_get_state.assert_any_call(self.supplier_ids[1])
            mock_get_state.assert_any_call(self.supplier_ids[2])
            
            # Verify that select_action was called with the right states - use any_call to avoid parameter matching issues
            calls = mock_select_action.call_args_list
            states_called = [call[0][0] for call in calls]  # Get the first positional arg (state) from each call
            self.assertIn(self.excellent_state, states_called)
            self.assertIn(self.good_state, states_called)
            self.assertIn(self.average_state, states_called)

    def test_ranking_service_records_events(self):
        """Test that RankingService records ranking events"""
        # Mock necessary methods
        with patch('ranking_engine.services.metrics_service.MetricsService.get_supplier_metrics') as mock_get_metrics, \
             patch('ranking_engine.services.supplier_service.SupplierService.get_supplier') as mock_get_supplier, \
             patch('ranking_engine.q_learning.state_mapper.StateMapper.get_supplier_state') as mock_get_state, \
             patch('ranking_engine.q_learning.agent.SupplierRankingAgent.select_action') as mock_select_action, \
             patch('connectors.user_service_connector.UserServiceConnector.get_active_suppliers') as mock_get_active_suppliers, \
             patch('connectors.user_service_connector.UserServiceConnector.get_supplier_by_id') as mock_get_supplier_by_id:
            
            # Mock active suppliers list
            mock_get_active_suppliers.return_value = [
                {'user': {'id': self.supplier_ids[0]}},
                {'user': {'id': self.supplier_ids[1]}},
                {'user': {'id': self.supplier_ids[2]}}
            ]
            
            # Mock supplier_by_id to return supplier data
            mock_get_supplier_by_id.side_effect = lambda supplier_id: {
                'company_name': f'Supplier {supplier_id}',
                'compliance_score': 8.0 if supplier_id == self.supplier_ids[0] else 7.0
            }
            
            # Set up supplier service mock
            mock_get_supplier.side_effect = lambda supplier_id: {
                'company_name': f'Supplier {supplier_id}',
                'compliance_score': 7.0
            }
            
            # Set up metrics service mock
            mock_get_metrics.side_effect = lambda supplier_id: {
                'quality_score': 9.0 if supplier_id == self.supplier_ids[0] else 7.0,
                'delivery_score': 9.0 if supplier_id == self.supplier_ids[0] else 7.0,
                'price_score': 9.0 if supplier_id == self.supplier_ids[0] else 7.0,
                'service_score': 9.0 if supplier_id == self.supplier_ids[0] else 7.0,
                'overall_score': 9.0 if supplier_id == self.supplier_ids[0] else 7.0
            }
            
            # Set up state mapper mock
            mock_get_state.side_effect = lambda supplier_id: (
                self.excellent_state if supplier_id == self.supplier_ids[0] else
                self.good_state
            )
            
            # Set up agent mock - use *args, **kwargs to handle any parameter signature
            mock_select_action.side_effect = lambda state, *args, **kwargs: (
                self.rank_tier_1 if state == self.excellent_state else
                self.rank_tier_2
            )
            
            # Call generate_rankings
            self.ranking_service.generate_rankings()
            
            # Verify ranking events were created
            events = RankingEvent.objects.filter(event_type='SUPPLIER_RANKED')
            self.assertGreaterEqual(len(events), 3)  # At least one event per supplier
            
            # Verify event data for excellent supplier
            excellent_events = events.filter(supplier_id=self.supplier_ids[0])
            self.assertGreaterEqual(len(excellent_events), 1)
            event = excellent_events.first()
            self.assertIn('action', event.metadata)
            self.assertIn('state', event.metadata)
            self.assertEqual(event.metadata['action'], 'RANK_TIER_1')
            self.assertEqual(event.metadata['state'], 'Q5_D5_P5_S5')
            
            # Verify ranking was correctly mapped to a tier
            self.assertIn('tier', event.metadata)
            self.assertEqual(event.metadata['tier'], 1)  # RANK_TIER_1 maps to tier 1

    def test_ranking_service_with_real_agent(self):
        """Test RankingService with an actual SupplierRankingAgent instance"""
        # Create a real agent
        agent = SupplierRankingAgent(config=self.config)
        
        # Mock necessary methods
        with patch('ranking_engine.services.metrics_service.MetricsService.get_supplier_metrics') as mock_get_metrics, \
             patch('ranking_engine.services.supplier_service.SupplierService.get_supplier') as mock_get_supplier, \
             patch('ranking_engine.q_learning.state_mapper.StateMapper.get_supplier_state') as mock_get_state, \
             patch('ranking_engine.services.ranking_service.RankingService._create_agent') as mock_create_agent, \
             patch('connectors.user_service_connector.UserServiceConnector.get_active_suppliers') as mock_get_active_suppliers, \
             patch('connectors.user_service_connector.UserServiceConnector.get_supplier_by_id') as mock_get_supplier_by_id:
            
            # Make the service use our real agent
            mock_create_agent.return_value = agent
            
            # Mock active suppliers list
            mock_get_active_suppliers.return_value = [
                {'user': {'id': self.supplier_ids[0]}},
                {'user': {'id': self.supplier_ids[1]}},
                {'user': {'id': self.supplier_ids[2]}}
            ]
            
            # Mock supplier_by_id to return supplier data
            mock_get_supplier_by_id.side_effect = lambda supplier_id: {
                'company_name': f'Supplier {supplier_id}',
                'compliance_score': 8.0 if supplier_id == self.supplier_ids[0] else 
                                   7.0 if supplier_id == self.supplier_ids[1] else 5.0
            }
            
            # Set up supplier service mock
            mock_get_supplier.side_effect = lambda supplier_id: {
                'company_name': f'Supplier {supplier_id}',
                'compliance_score': 7.0
            }
            
            # Set up metrics service mock
            mock_get_metrics.side_effect = lambda supplier_id: {
                'quality_score': 9.0 if supplier_id == self.supplier_ids[0] else 7.0,
                'delivery_score': 9.0 if supplier_id == self.supplier_ids[0] else 7.0,
                'price_score': 9.0 if supplier_id == self.supplier_ids[0] else 7.0,
                'service_score': 9.0 if supplier_id == self.supplier_ids[0] else 7.0,
                'overall_score': 9.0 if supplier_id == self.supplier_ids[0] else 7.0
            }
            
            # Set up state mapper mock
            mock_get_state.side_effect = lambda supplier_id: (
                self.excellent_state if supplier_id == self.supplier_ids[0] else
                self.good_state if supplier_id == self.supplier_ids[1] else
                self.average_state
            )
            
            # Call generate_rankings
            self.ranking_service.generate_rankings()
            
            # Verify rankings were created
            rankings = SupplierRanking.objects.all().order_by('rank')
            self.assertEqual(len(rankings), 3)
            
            # Verify excellent supplier gets rank 1 and tier 1
            excellent_ranking = SupplierRanking.objects.get(supplier_id=self.supplier_ids[0])
            self.assertEqual(excellent_ranking.rank, 1)
            self.assertEqual(excellent_ranking.tier, 1)
            
            # Verify good supplier gets tier 2
            good_ranking = SupplierRanking.objects.get(supplier_id=self.supplier_ids[1])
            self.assertEqual(good_ranking.tier, 2)
            
            # Verify average supplier gets tier 3
            avg_ranking = SupplierRanking.objects.get(supplier_id=self.supplier_ids[2])
            self.assertEqual(avg_ranking.tier, 3)

if __name__ == '__main__':
    unittest.main() 