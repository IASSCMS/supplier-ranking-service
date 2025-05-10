"""
Ranking Service - Orchestrates the supplier ranking process

This service coordinates the calculation of metrics, Q-Learning algorithm execution,
and generation/storage of supplier rankings.
"""

from django.db import transaction
from django.utils import timezone
from datetime import date, datetime

from api.models import (
    SupplierRanking,
    RankingEvent,
    SupplierPerformanceCache
)

from ranking_engine.services.metrics_service import MetricsService
from ranking_engine.q_learning.agent import SupplierRankingAgent
from ranking_engine.q_learning.environment import SupplierEnvironment
from ranking_engine.q_learning.state_mapper import StateMapper
from connectors.user_service_connector import UserServiceConnector


class RankingService:
    """
    Service for generating and managing supplier rankings
    """
    
    def __init__(self):
        """
        Initialize the ranking service with a q-learning agent and state mapper
        """
        self.user_service = UserServiceConnector()
        self.metrics_service = MetricsService()
        self.agent = self._create_agent()
        self.environment = SupplierEnvironment()
        self.state_mapper = StateMapper()
        self.initialize_q_learning()

    def _create_agent(self):
        """
        Creates and returns a SupplierRankingAgent instance
        """
        return SupplierRankingAgent()

    @staticmethod
    def initialize_q_learning():
        """
        Initializes the Q-Learning components and returns
        the agent, environment, and state mapper
        """
        agent = SupplierRankingAgent()
        environment = SupplierEnvironment()
        state_mapper = StateMapper()
        return agent, environment, state_mapper

    @staticmethod
    def update_supplier_ranking(supplier_id, action, state):
        """
        Creates or updates a supplier ranking record using the environment's update_rankings
        """
        try:
            ranking = SupplierEnvironment().update_rankings(supplier_id, action)
            return ranking
        except Exception as e:
            RankingEvent.objects.create(
                event_type='ERROR',
                description=f"Error updating ranking for supplier {supplier_id}: {str(e)}",
                supplier_id=supplier_id
            )
            return None

    @staticmethod
    def generate_supplier_rankings(days=90):
        """
        Generates rankings for all active suppliers using the Q-Learning approach
        """
        agent = SupplierRankingAgent()
        environment = SupplierEnvironment()
        metrics_service = MetricsService()
        state_mapper = StateMapper()
        user_service = UserServiceConnector()

        # Get all supplier IDs (from user service)
        suppliers = user_service.get_active_suppliers()
        if not suppliers:
            RankingEvent.objects.create(
                event_type='ERROR',
                description="No active suppliers found"
            )
            return []
        
        supplier_ids = [s['user']['id'] for s in suppliers]

        RankingEvent.objects.create(
            event_type='RANKING_STARTED',
            description=f"Starting ranking process for {len(supplier_ids)} suppliers"
        )

        rankings = []
        ranking_date = date.today()
        
        # First process all suppliers to calculate metrics and scores
        for supplier_id in supplier_ids:
            # Get supplier data
            supplier_data = user_service.get_supplier_by_id(supplier_id)
            if not supplier_data:
                continue
            
            # Calculate metrics
            metrics = metrics_service.calculate_combined_metrics(supplier_id, days)
            
            # Create or update SupplierRanking object
            try:
                ranking = SupplierRanking.objects.get(
                    supplier_id=supplier_id,
                    date=ranking_date
                )
            except SupplierRanking.DoesNotExist:
                ranking = SupplierRanking(
                    supplier_id=supplier_id,
                    supplier_name=supplier_data.get('company_name', f"Supplier {supplier_id}"),
                    date=ranking_date,
                    rank=0  # Will be updated later
                )
            
            # Update scores
            ranking.overall_score = metrics['overall_score']
            ranking.quality_score = metrics['quality_score']
            ranking.delivery_score = metrics['delivery_score']
            ranking.price_score = metrics['price_score']
            ranking.service_score = metrics['service_score']
            
            # Get the state based on metrics
            state = state_mapper.get_state_from_metrics(metrics)
            ranking.state = state
            
            # Save the ranking without final rank yet
            ranking.save()
            rankings.append(ranking)
            
            # Log action taken
            RankingEvent.objects.create(
                event_type='RECOMMENDATION_MADE',
                description=f"Calculated metrics for supplier {supplier_id}",
                supplier_id=supplier_id
            )

        # Now sort by overall score and assign ranks
        sorted_rankings = SupplierRanking.objects.filter(
            date=ranking_date
        ).order_by('-overall_score')
        
        # Assign ranks (1 = highest score)
        for i, ranking in enumerate(sorted_rankings):
            ranking.rank = i + 1
            ranking.save(update_fields=['rank'])
            
            # Use agent to get recommended action based on supplier's state
            state = ranking.state
            if state:
                actions = environment.get_actions(state)
                if actions:
                    action = agent.get_best_action(state)
                    if action:
                        # Log the action but don't apply it automatically
                        RankingEvent.objects.create(
                            event_type='RECOMMENDATION_MADE',
                            description=f"Recommended action {action.name} for supplier {ranking.supplier_id}",
                            supplier_id=ranking.supplier_id,
                            state_id=state.id if state else None,
                            action_id=action.id if action else None
                        )

        RankingEvent.objects.create(
            event_type='RANKING_COMPLETED',
            description=f"Completed ranking process for {len(rankings)} suppliers"
        )
        
        # Refresh the rankings to get the updated ranks
        return SupplierRanking.objects.filter(date=ranking_date).order_by('rank')

    @staticmethod
    @transaction.atomic
    def process_supplier_ranking_batch(batch_id=None):
        """
        Processes supplier rankings in a single transaction
        with optional batch tracking
        """
        rankings = RankingService.generate_supplier_rankings()
        summary = {
            'batch_id': batch_id or f"batch_{date.today().strftime('%Y%m%d')}",
            'timestamp': timezone.now(),
            'suppliers_ranked': len(rankings),
            'top_ranked': [],
            'bottom_ranked': [],
            'average_score': 0
        }
        if rankings:
            total_score = sum(r.overall_score for r in rankings if r is not None)
            summary['average_score'] = total_score / len(rankings)
            top_suppliers = SupplierRanking.objects.filter(date=date.today()).order_by('rank')[:5]
            bottom_suppliers = SupplierRanking.objects.filter(date=date.today()).order_by('-rank')[:5]
            summary['top_ranked'] = [
                {
                    'supplier_id': r.supplier_id,
                    'supplier_name': r.supplier_name,
                    'rank': r.rank,
                    'score': r.overall_score
                }
                for r in top_suppliers
            ]
            summary['bottom_ranked'] = [
                {
                    'supplier_id': r.supplier_id,
                    'supplier_name': r.supplier_name,
                    'rank': r.rank,
                    'score': r.overall_score
                }
                for r in bottom_suppliers
            ]
        return summary

    def generate_rankings(self, ranking_date=None):
        """
        Generate rankings for a specific date (for test compatibility)
        """
        if ranking_date is None:
            ranking_date = date.today()
            
        user_service = self.user_service
        
        # Get all supplier IDs (from user service)
        suppliers = user_service.get_active_suppliers()
        if not suppliers:
            RankingEvent.objects.create(
                event_type='ERROR',
                description="No active suppliers found"
            )
            return []
        
        supplier_ids = [s['user']['id'] for s in suppliers]
        
        RankingEvent.objects.create(
            event_type='RANKING_STARTED',
            description=f"Starting ranking process for {len(supplier_ids)} suppliers"
        )
        
        rankings = []
        
        # First process all suppliers to calculate metrics and scores
        for supplier_id in supplier_ids:
            # Get supplier data
            supplier_data = user_service.get_supplier_by_id(supplier_id)
            if not supplier_data:
                continue
            
            # Calculate metrics
            metrics = self.metrics_service.calculate_combined_metrics(supplier_id)
            
            # Get the supplier state
            state = self.state_mapper.get_supplier_state(supplier_id)
            
            # Get the best action using the agent
            action = self.agent.get_best_action(state)
            
            if not action:
                continue
                
            # Update the supplier ranking with the action
            ranking = self.update_supplier_ranking(supplier_id, action, state)
            if ranking:
                rankings.append(ranking)
                
                # Create a RankingEvent to record the action
                RankingEvent.objects.create(
                    event_type='SUPPLIER_RANKED',
                    description=f"Ranked supplier {supplier_id} as {action.name}",
                    supplier_id=supplier_id,
                    state_id=state.id if state else None,
                    action_id=action.id if action else None,
                    metadata={
                        'action': action.name,
                        'state': state.name,
                        'tier': ranking.tier,
                        'rank': ranking.rank,
                        'overall_score': ranking.overall_score
                    }
                )
            
        # Now sort by overall score and assign ranks
        sorted_rankings = SupplierRanking.objects.filter(
            date=ranking_date
        ).order_by('-overall_score')
        
        # Assign ranks (1 = highest score)
        for i, ranking in enumerate(sorted_rankings):
            ranking.rank = i + 1
            ranking.save(update_fields=['rank'])
        
        RankingEvent.objects.create(
            event_type='RANKING_COMPLETED',
            description=f"Completed ranking process for {len(rankings)} suppliers"
        )
        
        # Return the sorted rankings
        return sorted_rankings

    def update_q_values_from_transactions(self, transactions):
        """
        Updates Q-values based on supplier transaction data using the agent/environment
        """
        agent = self.agent
        environment = self.environment
        state_mapper = self.state_mapper
        from ranking_engine.utils.data_preprocessing import preprocess_supplier_data
        processed_data = preprocess_supplier_data(transactions)
        RankingEvent.objects.create(
            event_type='MODEL_TRAINED',
            description=f"Updating Q-values from {len(transactions)} transactions",
            metadata={
                'transaction_count': len(transactions),
                'supplier_count': len(processed_data)
            }
        )
        for supplier_id, metrics in processed_data.items():
            # Map metrics to state
            state = state_mapper.get_state_from_metrics(metrics)
            # Pick a default action (e.g., first available)
            actions = environment.get_actions(state)
            action = actions[0] if actions else None
            if action:
                reward = environment.get_reward(supplier_id, state, action)
                agent.update_q_table(state.name, action.name, reward)
            # Optionally update performance cache
            try:
                user_service = UserServiceConnector()
                supplier_data = user_service.get_supplier_by_id(supplier_id)
                supplier_name = supplier_data.get('company_name', f"Supplier {supplier_id}")
                SupplierPerformanceCache.objects.update_or_create(
                    supplier_id=supplier_id,
                    date=date.today(),
                    defaults={
                        'supplier_name': supplier_name,
                        'quality_score': metrics.get('quality_score', 8.5),
                        'defect_rate': metrics.get('defect_rate', 5.0),
                        'return_rate': metrics.get('return_rate', 5.0),
                        'on_time_delivery_rate': metrics.get('on_time_delivery_rate', 90.0),
                        'average_delay_days': metrics.get('average_delay_days', 1.0),
                        'price_competitiveness': metrics.get('price_score', 8.0),
                        'responsiveness': metrics.get('responsiveness', 8.0),
                        'fill_rate': metrics.get('fill_rate', 95.0),
                        'order_accuracy': metrics.get('order_accuracy', 95.0),
                        'data_complete': True
                    }
                )
            except Exception as e:
                RankingEvent.objects.create(
                    event_type='ERROR',
                    description=f"Error caching performance data for supplier {supplier_id}: {str(e)}",
                    supplier_id=supplier_id
                )