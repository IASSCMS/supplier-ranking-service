"""
Environment module for Q-Learning implementation.

This module simulates the supplier environment for the Q-Learning algorithm,
providing state transitions and rewards based on supplier actions.
"""

from api.models import (
    QLearningAction, QLearningState, RankingConfiguration, 
    SupplierRanking, SupplierPerformanceCache, RankingEvent
)
from django.db.models import Avg, Max, Min
from datetime import datetime, timedelta, date
import numpy as np
from ranking_engine.q_learning.state_mapper import StateMapper
from connectors.group29_connector import Group29Connector
from connectors.group30_connector import Group30Connector
from connectors.group32_connector import Group32Connector
from ranking_engine.services.supplier_service import SupplierService
from ranking_engine.services.metrics_service import MetricsService
from unittest.mock import MagicMock
import logging

logger = logging.getLogger(__name__)


class SupplierEnvironment:
    """
    Environment class for Q-Learning algorithm.
    
    This class simulates the supplier environment by providing state transitions
    and rewards based on supplier actions.
    """
    
    def __init__(self, config=None):
        """
        Initialize the supplier environment.
        
        Args:
            config (RankingConfiguration, optional): Configuration for the environment
        """
        # Get active configuration or default
        self.config = config or RankingConfiguration.objects.filter(is_active=True).first()
        if not self.config:
            # Create default configuration if none exists
            self.config = RankingConfiguration.objects.create(
                name="Default Configuration",
                learning_rate=0.1,
                discount_factor=0.9,
                exploration_rate=0.3,
                quality_weight=0.25,
                delivery_weight=0.25,
                price_weight=0.25,
                service_weight=0.25,
                is_active=True
            )
            
        # Initialize state mapper
        self.state_mapper = StateMapper()
        
        # Initialize connectors to external services
        self.supplier_service = SupplierService()
        self.metrics_service = MetricsService()
        self.demand_forecasting = Group29Connector()
        self.blockchain_tracking = Group30Connector()
        self.logistics = Group32Connector()
        
        # Initialize available actions
        self._initialize_actions()
    
    def _initialize_actions(self):
        """Initialize the available actions for the Q-Learning algorithm."""
        # Define standard actions for supplier ranking
        standard_actions = [
            {
                'name': 'RANK_TIER_1',
                'description': 'Rank the supplier as Tier 1 (Preferred)'
            },
            {
                'name': 'RANK_TIER_2',
                'description': 'Rank the supplier as Tier 2 (Approved)'
            },
            {
                'name': 'RANK_TIER_3',
                'description': 'Rank the supplier as Tier 3 (Conditional)'
            },
            {
                'name': 'RANK_TIER_4',
                'description': 'Rank the supplier as Tier 4 (Probationary)'
            },
            {
                'name': 'RANK_TIER_5',
                'description': 'Rank the supplier as Tier 5 (Not Recommended)'
            },
            {
                'name': 'INCREASE_ORDER_VOLUME',
                'description': 'Recommend increasing order volume with this supplier'
            },
            {
                'name': 'DECREASE_ORDER_VOLUME',
                'description': 'Recommend decreasing order volume with this supplier'
            },
            {
                'name': 'FLAG_FOR_AUDIT',
                'description': 'Flag supplier for audit due to concerns'
            },
            {
                'name': 'REQUEST_QUALITY_IMPROVEMENT',
                'description': 'Request supplier to improve quality'
            },
            {
                'name': 'REQUEST_DELIVERY_IMPROVEMENT',
                'description': 'Request supplier to improve delivery performance'
            }
        ]
        
        # Create actions in database if they don't exist
        for action_data in standard_actions:
            QLearningAction.objects.get_or_create(
                name=action_data['name'],
                defaults={'description': action_data['description']}
            )
    
    def get_supplier_performance(self, supplier_id):
        """
        Get supplier performance metrics from various services.
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            dict: Dictionary containing performance metrics
        """
        try:
            # Get supplier info from User Service
            supplier_info = self.supplier_service.get_supplier(supplier_id)
            
            if not supplier_info:
                logger.error(f"Supplier {supplier_id} not found")
                return None
            
            # Get metrics from various services
            quality_metrics = self.metrics_service.get_quality_metrics(supplier_id)
            delivery_metrics = self.metrics_service.get_delivery_metrics(supplier_id)
            price_metrics = self.metrics_service.get_price_metrics(supplier_id)
            service_metrics = self.metrics_service.get_service_metrics(supplier_id)
            
            # Get data from other services
            forecast_data = {}  # Would come from group 29
            logistics_data = {}  # Would come from group 32
            
            today = date.today()
            
            # Combine all metrics
            performance = {
                'quality_score': quality_metrics.get('quality_score', 8.0),
                'defect_rate': quality_metrics.get('defect_rate', 2.0),
                'return_rate': quality_metrics.get('return_rate', 1.0),
                'on_time_delivery_rate': delivery_metrics.get('on_time_delivery_rate', 95.0),
                'average_delay_days': delivery_metrics.get('average_delay_days', 0.0),
                'price_competitiveness': price_metrics.get('price_score', 7.0),
                'responsiveness': service_metrics.get('responsiveness', 8.0),
                'issue_resolution_time': service_metrics.get('issue_resolution_time', 0.0),
                'fill_rate': delivery_metrics.get('fill_rate', 100.0),
                'order_accuracy': delivery_metrics.get('order_accuracy', 100.0),
                'compliance_score': supplier_info.get('compliance_score', 5.0),
                'demand_forecast_accuracy': forecast_data.get('accuracy', 90.0),
                'logistics_efficiency': logistics_data.get('efficiency', 5.0)
            }
            
            # Cache the performance data for future use
            try:
                SupplierPerformanceCache.objects.update_or_create(
                    supplier_id=supplier_id,
                    date=today,
                    defaults={
                        'supplier_name': supplier_info.get('company_name', f"Supplier {supplier_id}"),
                        'quality_score': performance['quality_score'],
                        'defect_rate': performance['defect_rate'],
                        'return_rate': performance['return_rate'],
                        'on_time_delivery_rate': performance['on_time_delivery_rate'],
                        'average_delay_days': performance['average_delay_days'],
                        'price_competitiveness': performance['price_competitiveness'],
                        'responsiveness': performance['responsiveness'],
                        'issue_resolution_time': performance['issue_resolution_time'],
                        'fill_rate': performance['fill_rate'],
                        'order_accuracy': performance['order_accuracy'],
                        'compliance_score': performance['compliance_score'],
                        'demand_forecast_accuracy': performance['demand_forecast_accuracy'],
                        'logistics_efficiency': performance['logistics_efficiency'],
                        'data_complete': True
                    }
                )
            except Exception as e:
                RankingEvent.objects.create(
                    event_type='ERROR',
                    description=f"Failed to cache performance data: {str(e)}",
                    supplier_id=supplier_id,
                    metadata={'error': str(e)}
                )
            
            return performance
            
        except Exception as e:
            logger.error(f"Error getting supplier performance for supplier {supplier_id}: {str(e)}")
            return None
    
    def get_state(self, supplier_id):
        """
        Get the current state for a supplier.
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            QLearningState: State object
        """
        try:
            # Get state directly from state mapper
            return self.state_mapper.get_supplier_state(supplier_id)
            
        except Exception as e:
            logger.error(f"Error getting state for supplier {supplier_id}: {str(e)}")
            # Return a default "unknown" state
            unknown_state, _ = QLearningState.objects.get_or_create(
                name="unknown",
                defaults={'description': 'Unknown or error state'}
            )
            return unknown_state
    
    def get_actions(self, state):
        """
        Get available actions for a given state.
        
        Args:
            state (QLearningState): Current state
            
        Returns:
            list: List of available actions
        """
        # For now, return all actions
        # In a more complex implementation, actions could be state-dependent
        return list(QLearningAction.objects.all())
    
    def get_reward(self, supplier_id, state, action):
        """
        Calculate reward for a state-action pair.
        
        Args:
            supplier_id (int): ID of the supplier
            state (QLearningState): Current state
            action (QLearningAction): Action taken
            
        Returns:
            float: Reward value
        """
        try:
            # Get supplier metrics
            metrics = self.metrics_service.get_supplier_metrics(supplier_id)
            
            # Calculate reward based on metrics and action
            reward = 0.0
            
            # Example reward calculation
            if action.name == "promote":
                reward = metrics.get('quality_score', 0.0) * self.config.quality_weight + \
                         metrics.get('delivery_score', 0.0) * self.config.delivery_weight
            elif action.name == "maintain":
                reward = 0.0
            elif action.name == "demote":
                reward = -metrics.get('quality_score', 0.0) * self.config.quality_weight - \
                         metrics.get('delivery_score', 0.0) * self.config.delivery_weight
            elif action.name == "blacklist":
                reward = -1.0
            
            return reward
            
        except Exception as e:
            logger.error(f"Error calculating reward for supplier {supplier_id}: {str(e)}")
            return 0.0
    
    def next_state(self, supplier_id, action):
        """
        Get the next state after taking an action.
        
        Args:
            supplier_id (int): ID of the supplier
            action (QLearningAction): Action taken
            
        Returns:
            QLearningState: Next state object
        """
        try:
            # Get current state from the state mapper
            return self.state_mapper.get_supplier_state(supplier_id)
            
        except Exception as e:
            logger.error(f"Error getting next state for supplier {supplier_id}: {str(e)}")
            # Return a default "unknown" state
            unknown_state, _ = QLearningState.objects.get_or_create(
                name="unknown",
                defaults={'description': 'Unknown or error state'}
            )
            return unknown_state
    
    def update_rankings(self, supplier_id, action):
        """
        Update supplier rankings based on the action taken.
        
        Args:
            supplier_id (int): ID of the supplier
            action (QLearningAction): Action taken
            
        Returns:
            SupplierRanking: Updated ranking object
        """
        try:
            # Get supplier
            supplier = self.supplier_service.get_supplier(supplier_id)
            
            if not supplier:
                logger.error(f"Supplier with ID {supplier_id} does not exist or could not be fetched")
                return None
            
            today = date.today()
            
            # Get current ranking or create new one for today
            try:
                ranking = SupplierRanking.objects.get(supplier_id=supplier_id, date=today)
            except SupplierRanking.DoesNotExist:
                ranking = SupplierRanking(
                    supplier_id=supplier_id,
                    supplier_name=supplier.get('company_name', f"Supplier {supplier_id}"),
                    date=today,
                    rank=0,
                    overall_score=0.0,
                    quality_score=0.0,
                    delivery_score=0.0,
                    price_score=0.0,
                    service_score=0.0
                )
            
            # Update ranking based on action
            if action.name == "promote":
                ranking.rank = max(0, ranking.rank - 1)
            elif action.name == "demote":
                ranking.rank += 1
            elif action.name == "blacklist":
                ranking.rank = 999  # Blacklisted suppliers have a very high rank
            
            # Handle the RANK_TIER actions
            if action.name.startswith("RANK_TIER_"):
                try:
                    tier = int(action.name.split("_")[-1])
                    ranking.tier = tier
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse tier from action name: {action.name}")
            
            # Update score based on metrics
            try:
                metrics = self.metrics_service.get_supplier_metrics(supplier_id)
            except Exception as e:
                logger.error(f"Error getting metrics for supplier {supplier_id}: {str(e)}")
                # Use default metrics as fallback
                metrics = {
                    'quality_score': 7.0,
                    'delivery_score': 7.0,
                    'price_score': 7.0,
                    'service_score': 7.0,
                    'overall_score': 7.0
                }
            
            # Get compliance score from supplier data
            compliance_score = supplier.get('compliance_score', 5.0)
            
            # Set all individual scores
            ranking.quality_score = metrics.get('quality_score', 0.0)
            ranking.delivery_score = metrics.get('delivery_score', 0.0)
            ranking.price_score = metrics.get('price_score', 0.0)
            ranking.service_score = metrics.get('service_score', 0.0)
            
            # Calculate overall score with weights from config
            base_score = (
                ranking.quality_score * self.config.quality_weight +
                ranking.delivery_score * self.config.delivery_weight +
                ranking.price_score * self.config.price_weight +
                ranking.service_score * self.config.service_weight
            )
            
            # Add compliance score influence (20% weight)
            ranking.overall_score = base_score * 0.8 + compliance_score * 0.2
            
            ranking.save()
            
            # After saving individual ranking, recalculate all ranks
            # to ensure they are in proper order
            self._recalculate_ranks(today)
            
            # Refresh the ranking object to get the updated rank
            ranking.refresh_from_db()
            
            return ranking
            
        except Exception as e:
            logger.error(f"Error updating rankings for supplier {supplier_id}: {str(e)}")
            return None
    
    def _recalculate_ranks(self, ranking_date=None):
        """
        Recalculate ranks for all suppliers for a given date
        based on their overall_score
        
        Args:
            ranking_date (date): Date to recalculate rankings for
        """
        if ranking_date is None:
            ranking_date = date.today()
        
        # Get all rankings for the date, ordered by overall_score (descending)
        rankings = SupplierRanking.objects.filter(date=ranking_date).order_by('-overall_score')
        
        # Assign ranks (1 = highest score)
        for i, ranking in enumerate(rankings):
            ranking.rank = i + 1
            ranking.save(update_fields=['rank'])
        
    def get_performance(self, supplier_id):
        return MetricsService().calculate_combined_metrics(supplier_id)  # Use full metrics[4][5]