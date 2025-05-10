"""
Live Integration Test for Supplier Ranking System

This test module uses real service connectors instead of mocks to test
the full supplier ranking workflow in an integration environment.
"""

from django.test import TestCase
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta

# Import models
from api.models import (
    SupplierRanking,
    RankingEvent,
    QLearningState,
    QLearningAction,
    QTableEntry,
    RankingConfiguration
)

# Import services
from ranking_engine.services.ranking_service import RankingService
from ranking_engine.services.metrics_service import MetricsService
from ranking_engine.services.supplier_service import SupplierService
from ranking_engine.q_learning.agent import SupplierRankingAgent
from ranking_engine.q_learning.environment import SupplierEnvironment
from ranking_engine.q_learning.state_mapper import StateMapper

# Import connectors
from connectors.user_service_connector import UserServiceConnector
from connectors.warehouse_service_connector import WarehouseServiceConnector
from connectors.order_service_connector import OrderServiceConnector
from connectors.group29_connector import Group29Connector
from connectors.group30_connector import Group30Connector
from connectors.group32_connector import Group32Connector

import logging

# Configure logging
logger = logging.getLogger(__name__)


class TestLiveIntegration(TestCase):
    """
    Live integration tests for the supplier ranking system using actual services.
    
    NOTE: These tests will connect to live services and are meant to verify
    integration in a test or staging environment, not for regular CI/CD runs.
    """
    
    def setUp(self):
        """Set up the test environment."""
        # Create a test configuration
        self.config = RankingConfiguration.objects.create(
            name="Test Live Integration Config",
            learning_rate=0.1,
            discount_factor=0.9,
            exploration_rate=0.2,
            quality_weight=0.25,
            delivery_weight=0.25,
            price_weight=0.25,
            service_weight=0.25,
            is_active=True
        )
        
        # Initialize real services (not mocked)
        self.user_service = UserServiceConnector()
        self.warehouse_service = WarehouseServiceConnector()
        self.order_service = OrderServiceConnector()
        self.group29_connector = Group29Connector()
        self.group30_connector = Group30Connector()
        self.group32_connector = Group32Connector()
        
        # Initialize core services
        self.supplier_service = SupplierService()
        self.metrics_service = MetricsService()
        self.state_mapper = StateMapper()
        self.environment = SupplierEnvironment(config=self.config)
        self.agent = SupplierRankingAgent(config=self.config)
        
        # Initialize the ranking service
        self.ranking_service = RankingService()
        
        # Get list of active supplier IDs for testing
        self.active_supplier_ids = self.supplier_service.get_active_supplier_ids()
        # Use a subset for testing if there are too many suppliers
        if len(self.active_supplier_ids) > 3:
            self.test_supplier_ids = self.active_supplier_ids[:3]
        else:
            self.test_supplier_ids = self.active_supplier_ids
            
        # Log test setup
        logger.info(f"Setting up live integration test with {len(self.test_supplier_ids)} suppliers")
        for supplier_id in self.test_supplier_ids:
            logger.info(f"Test supplier ID: {supplier_id}")

    def test_get_supplier_data(self):
        """Test fetching real supplier data from the user service."""
        if not self.test_supplier_ids:
            self.skipTest("No active suppliers available for testing")
            
        for supplier_id in self.test_supplier_ids:
            supplier = self.supplier_service.get_supplier(supplier_id)
            self.assertIsNotNone(supplier, f"Failed to retrieve supplier {supplier_id}")
            
            # Check for different supplier data structures
            # Some implementations use supplier['id'], others use supplier['user']['id']
            supplier_id_from_data = None
            if 'id' in supplier:
                supplier_id_from_data = supplier['id']
            elif 'user' in supplier and 'id' in supplier['user']:
                supplier_id_from_data = supplier['user']['id']
            
            self.assertIsNotNone(supplier_id_from_data, f"Could not find ID in supplier data: {supplier}")
            self.assertEqual(supplier_id_from_data, supplier_id, "Supplier ID mismatch")
            
            # Get company name with fallback
            company_name = supplier.get('company_name', 
                           supplier.get('name',
                           supplier.get('user', {}).get('name', f"Unknown Supplier {supplier_id}")))
            
            # Log the supplier data
            logger.info(f"Retrieved supplier: {company_name} (ID: {supplier_id})")

    def test_calculate_live_metrics(self):
        """Test calculating metrics for suppliers using real service data."""
        if not self.test_supplier_ids:
            self.skipTest("No active suppliers available for testing")
            
        for supplier_id in self.test_supplier_ids:
            # Calculate all metrics
            metrics = self.metrics_service.calculate_combined_metrics(supplier_id)
            
            # Verify metrics structure
            self.assertIsNotNone(metrics, f"Failed to calculate metrics for supplier {supplier_id}")
            self.assertIn('overall_score', metrics, "Overall score missing from metrics")
            self.assertIn('quality_score', metrics, "Quality score missing from metrics")
            self.assertIn('delivery_score', metrics, "Delivery score missing from metrics")
            self.assertIn('price_score', metrics, "Price score missing from metrics")
            self.assertIn('service_score', metrics, "Service score missing from metrics")
            
            # Log the metrics
            logger.info(f"Metrics for supplier {supplier_id}: Overall={metrics['overall_score']}, "
                       f"Quality={metrics['quality_score']}, Delivery={metrics['delivery_score']}, "
                       f"Price={metrics['price_score']}, Service={metrics['service_score']}")

    def test_q_learning_state_mapping(self):
        """Test mapping metrics to Q-learning states using real data."""
        if not self.test_supplier_ids:
            self.skipTest("No active suppliers available for testing")
            
        for supplier_id in self.test_supplier_ids:
            # Get metrics
            metrics = self.metrics_service.calculate_combined_metrics(supplier_id)
            
            # Map to state
            state = self.state_mapper.get_state_from_metrics(metrics)
            
            # Verify state
            self.assertIsNotNone(state, f"Failed to map state for supplier {supplier_id}")
            self.assertIsInstance(state, QLearningState, "State is not a QLearningState instance")
            
            # Log the state
            logger.info(f"State for supplier {supplier_id}: {state.name}")

    def test_environment_integration(self):
        """Test supplier environment with real data."""
        if not self.test_supplier_ids:
            self.skipTest("No active suppliers available for testing")
            
        for supplier_id in self.test_supplier_ids:
            # Get current state
            state = self.environment.get_state(supplier_id)
            
            # Get available actions
            actions = self.environment.get_actions(state)
            
            # Verify we have actions
            self.assertTrue(len(actions) > 0, f"No actions available for supplier {supplier_id}")
            
            # Pick the first action to test reward calculation
            test_action = actions[0]
            
            # Get reward
            reward = self.environment.get_reward(supplier_id, state, test_action)
            
            # Verify reward
            self.assertIsNotNone(reward, f"Failed to calculate reward for supplier {supplier_id}")
            
            # Get next state
            next_state = self.environment.next_state(supplier_id, test_action)
            
            # Verify next state
            self.assertIsNotNone(next_state, f"Failed to determine next state for supplier {supplier_id}")
            
            # Log the environment data
            logger.info(f"Environment data for supplier {supplier_id}: "
                       f"State={state.name}, Action={test_action.name}, "
                       f"Reward={reward}, Next State={next_state.name}")

    def test_agent_learning(self):
        """Test agent learning with real data."""
        if not self.test_supplier_ids:
            self.skipTest("No active suppliers available for testing")
            
        # Only use the first supplier for agent learning test
        supplier_id = self.test_supplier_ids[0]
        
        # Get current state
        state = self.environment.get_state(supplier_id)
        
        # Get available actions
        actions = self.environment.get_actions(state)
        
        # Select an action
        action = self.agent.select_action(state, actions)
        
        # Get reward
        reward = self.environment.get_reward(supplier_id, state, action)
        
        # Get next state
        next_state = self.environment.next_state(supplier_id, action)
        
        # Learn from this experience
        new_q_value = self.agent.learn(state, action, reward, next_state)
        
        # Verify learning occurred
        self.assertIsNotNone(new_q_value, "Failed to update Q-value")
        
        # Get the updated Q-value from the database
        q_entry = QTableEntry.objects.get(state=state, action=action)
        
        # Verify Q-value was saved
        self.assertEqual(q_entry.q_value, new_q_value, "Q-value not saved correctly")
        
        # Log the learning data
        logger.info(f"Agent learning for supplier {supplier_id}: "
                   f"State={state.name}, Action={action.name}, "
                   f"Reward={reward}, Next State={next_state.name}, "
                   f"New Q-value={new_q_value}")

    @transaction.atomic
    def test_end_to_end_ranking_process(self):
        """Test the complete ranking process with real data."""
        # Generate rankings
        rankings = self.ranking_service.generate_rankings()
        
        # Verify rankings were generated
        self.assertTrue(len(rankings) > 0, "No rankings were generated")
        
        # Check that ranking events were recorded
        events = RankingEvent.objects.filter(event_type='RANKING_COMPLETED')
        self.assertTrue(events.exists(), "No ranking completion event was recorded")
        
        # Log the rankings
        logger.info(f"Generated {len(rankings)} rankings")
        for i, ranking in enumerate(rankings[:5]):  # Log top 5 rankings
            logger.info(f"Rank {ranking.rank}: Supplier {ranking.supplier_id} - "
                       f"Score: {ranking.overall_score}")
            
        # Test batch processing
        batch_summary = self.ranking_service.process_supplier_ranking_batch()
        
        # Verify batch summary
        self.assertIsNotNone(batch_summary, "No batch summary was generated")
        self.assertIn('suppliers_ranked', batch_summary, "Suppliers ranked missing from batch summary")
        self.assertIn('average_score', batch_summary, "Average score missing from batch summary")
        
        # Log the batch summary
        logger.info(f"Batch summary: {batch_summary}") 