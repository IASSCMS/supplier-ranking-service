"""
State mapper module for Q-Learning implementation.

This module is responsible for mapping supplier data to states that can be used by the Q-Learning algorithm.
It categorizes supplier performance metrics into discrete states that the Q-Learning agent can work with.
"""

from api.models import QLearningState, SupplierPerformanceCache, RankingEvent
from django.db.models import Avg
from datetime import datetime, timedelta
import numpy as np
import logging

# Import connectors for external services
from connectors.group29_connector import Group29Connector
from connectors.group30_connector import Group30Connector
from connectors.group32_connector import Group32Connector

# Import service clients
from ranking_engine.services.integration_service import IntegrationService
from ranking_engine.services.metrics_service import MetricsService
from ranking_engine.services.supplier_service import SupplierService

logger = logging.getLogger(__name__)

class StateMapper:
    """
    Maps supplier data to states for Q-Learning algorithm.
    
    This class contains methods for converting supplier performance metrics into 
    discrete states that can be used by the Q-Learning algorithm. It fetches data
    from external services via connectors when necessary.
    """
    
    # Define thresholds for different metrics
    QUALITY_THRESHOLDS = [3.0, 5.0, 7.0, 9.0]  # Poor, Average, Good, Excellent
    DELIVERY_THRESHOLDS = [70, 80, 90, 95]     # % on-time delivery
    PRICE_THRESHOLDS = [3.0, 5.0, 7.0, 9.0]    # Price competitiveness score
    SERVICE_THRESHOLDS = [3.0, 5.0, 7.0, 9.0]  # Service quality score
    
    def __init__(self, time_window=30):
        """
        Initialize the StateMapper.
        
        Args:
            time_window (int): Time window in days for metrics calculation
        """
        self.time_window = time_window
        self.integration_service = IntegrationService()
        self.metrics_service = MetricsService()
        self.supplier_service = SupplierService()
        
        # Initialize connectors
        self.forecasting_connector = Group29Connector()
        self.blockchain_connector = Group30Connector()
        self.logistics_connector = Group32Connector()
    
    def get_supplier_state(self, supplier_id):
        """
        Get the current state for a specific supplier based on their recent performance.
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            QLearningState: State object
        """
        try:
            # Get supplier metrics
            metrics = self.metrics_service.get_supplier_metrics(supplier_id)
            
            # Map metrics to state
            return self.get_state_from_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Error getting state for supplier {supplier_id}: {str(e)}")
            # Return a default "unknown" state
            unknown_state, _ = QLearningState.objects.get_or_create(
                name="unknown",
                defaults={'description': 'Unknown or error state'}
            )
            return unknown_state
    
    def get_default_state(self):
        """
        Get a default state when supplier data cannot be retrieved.
        
        Returns:
            QLearningState: Default state object
        """
        unknown_state, _ = QLearningState.objects.get_or_create(
            name="unknown",
            defaults={'description': 'Unknown or error state'}
        )
        return unknown_state
    
    def get_state_from_metrics(self, metrics):
        """
        Map supplier metrics to a state.
        
        Args:
            metrics (dict): Supplier performance metrics
            
        Returns:
            QLearningState: State object
        """
        try:
            # Extract metrics
            quality_score = metrics.get('quality_score', 0.0)
            delivery_score = metrics.get('delivery_score', 0.0)
            price_score = metrics.get('price_score', 0.0)
            service_score = metrics.get('service_score', 0.0)
            
            # Map scores to discrete levels (1-5)
            quality_level = self._map_score_to_level(quality_score)
            delivery_level = self._map_score_to_level(delivery_score)
            price_level = self._map_score_to_level(price_score)
            service_level = self._map_score_to_level(service_score)
            
            # Create state name
            state_name = f"Q{quality_level}_D{delivery_level}_P{price_level}_S{service_level}"
            
            # Get or create state
            state, created = QLearningState.objects.get_or_create(
                name=state_name,
                defaults={'description': f'State with quality={quality_level}, delivery={delivery_level}, price={price_level}, service={service_level}'}
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Error mapping metrics to state: {str(e)}")
            # Return a default "unknown" state
            unknown_state, _ = QLearningState.objects.get_or_create(
                name="unknown",
                defaults={'description': 'Unknown or error state'}
            )
            return unknown_state
    
    def _map_score_to_level(self, score):
        """
        Map a continuous score to a discrete level (1-5).
        
        Args:
            score (float): Continuous score (0-10)
            
        Returns:
            int: Discrete level (1-5)
        """
        if score >= 8.0:
            return 5
        elif score >= 6.0:
            return 4
        elif score >= 4.0:
            return 3
        elif score >= 2.0:
            return 2
        else:
            return 1
    
    def _get_cached_metrics(self, supplier_id):
        """
        Retrieve metrics from the performance cache if available.
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            dict: Cached metrics
        """
        today = datetime.now().date()
        cutoff_date = today - timedelta(days=self.time_window)
        
        # Try to get the most recent cache entry
        recent_cache = SupplierPerformanceCache.objects.filter(
            supplier_id=supplier_id,
            date__gte=cutoff_date,
            data_complete=True
        ).order_by('-date').first()
        
        if recent_cache:
            metrics = {
                'quality_score': recent_cache.quality_score,
                'defect_rate': recent_cache.defect_rate,
                'on_time_delivery_rate': recent_cache.on_time_delivery_rate,
                'price_competitiveness': recent_cache.price_competitiveness,
                'responsiveness': recent_cache.responsiveness,
                'service_score': (recent_cache.responsiveness + 
                                 (recent_cache.compliance_score or 5.0)) / 2
            }
            return metrics
        
        return None
    
    def _calculate_supplier_metrics(self, supplier_id):
        """
        Calculate performance metrics for a supplier by fetching data from external services.
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            dict: Calculated metrics
        """
        metrics = {}
        today = datetime.now().date()
        cutoff_date = today - timedelta(days=self.time_window)
        
        try:
            # Get supplier info from User Service
            supplier_info = self.integration_service.get_supplier_info(supplier_id)
            supplier_name = supplier_info.get('company_name', f"Supplier {supplier_id}")
            
            # Get quality and delivery metrics from Order Management Service
            order_metrics = self.integration_service.get_supplier_order_metrics(
                supplier_id, 
                cutoff_date.strftime('%Y-%m-%d'), 
                today.strftime('%Y-%m-%d')
            )
            
            # Extract metrics from order data
            metrics['quality_score'] = order_metrics.get('quality_score', 5.0)
            metrics['defect_rate'] = order_metrics.get('defect_rate', 0.0)
            metrics['on_time_delivery_rate'] = order_metrics.get('on_time_delivery_rate', 80.0)
            
            # Get price metrics from Warehouse Management Service
            price_data = self.integration_service.get_supplier_price_metrics(supplier_id)
            metrics['price_competitiveness'] = price_data.get('price_competitiveness', 5.0)
            
            # Get service metrics
            service_data = self.integration_service.get_supplier_service_metrics(supplier_id)
            metrics['responsiveness'] = service_data.get('responsiveness', 5.0)
            compliance_score = service_data.get('compliance_score', 5.0)
            metrics['service_score'] = (metrics['responsiveness'] + compliance_score) / 2
            
            # Get blockchain data if available
            try:
                blockchain_data = self.blockchain_connector.get_supplier_transactions(supplier_id, cutoff_date)
                if blockchain_data:
                    # Enhance delivery metrics with blockchain data
                    if 'delivery_performance' in blockchain_data:
                        blockchain_delivery = blockchain_data['delivery_performance']
                        # Blend with existing metrics (70% weight to blockchain verified data)
                        metrics['on_time_delivery_rate'] = (
                            0.3 * metrics['on_time_delivery_rate'] + 
                            0.7 * blockchain_delivery.get('on_time_percentage', metrics['on_time_delivery_rate'])
                        )
            except Exception as e:
                logger.warning(f"Failed to get blockchain data for supplier {supplier_id}: {str(e)}")
            
            # Get logistics data if available
            try:
                logistics_data = self.logistics_connector.get_supplier_logistics_data(supplier_id, cutoff_date)
                if logistics_data and 'logistics_efficiency' in logistics_data:
                    logistics_efficiency = logistics_data['logistics_efficiency']
                    # Could use this to further adjust delivery scores
                    if metrics['on_time_delivery_rate'] < 90 and logistics_efficiency > 7:
                        # If logistics are efficient but delivery rates are low, 
                        # the issue might be with the supplier's internal processes
                        pass
            except Exception as e:
                logger.warning(f"Failed to get logistics data for supplier {supplier_id}: {str(e)}")
            
            # Get demand forecasting data if available
            try:
                forecast_data = self.forecasting_connector.get_supplier_forecast_accuracy(supplier_id)
                if forecast_data and 'forecast_accuracy' in forecast_data:
                    # Could use this to adjust supplier rankings based on forecast accuracy
                    pass
            except Exception as e:
                logger.warning(f"Failed to get forecast data for supplier {supplier_id}: {str(e)}")
            
            # Create or update cache entry
            self._update_performance_cache(supplier_id, supplier_name, metrics)
            
        except Exception as e:
            logger.error(f"Error calculating metrics for supplier {supplier_id}: {str(e)}")
            # Return default metrics if there's an error
            metrics = {
                'quality_score': 5.0,
                'defect_rate': 0.0,
                'on_time_delivery_rate': 80.0,
                'price_competitiveness': 5.0,
                'responsiveness': 5.0,
                'service_score': 5.0
            }
        
        return metrics
    
    def _update_performance_cache(self, supplier_id, supplier_name, metrics):
        """
        Update the supplier performance cache with new metrics.
        
        Args:
            supplier_id (int): ID of the supplier
            supplier_name (str): Name of the supplier
            metrics (dict): Dictionary of metrics to cache
        """
        today = datetime.now().date()
        
        # Create or update cache entry
        cache_entry, created = SupplierPerformanceCache.objects.update_or_create(
            supplier_id=supplier_id,
            date=today,
            defaults={
                'supplier_name': supplier_name,
                'quality_score': metrics.get('quality_score', 5.0),
                'defect_rate': metrics.get('defect_rate', 0.0),
                'return_rate': metrics.get('return_rate', 0.0),
                'on_time_delivery_rate': metrics.get('on_time_delivery_rate', 80.0),
                'average_delay_days': metrics.get('avg_delay_days', 0.0),
                'price_competitiveness': metrics.get('price_competitiveness', 5.0),
                'responsiveness': metrics.get('responsiveness', 5.0),
                'issue_resolution_time': metrics.get('issue_resolution_time', None),
                'fill_rate': metrics.get('fill_rate', 95.0),
                'order_accuracy': metrics.get('order_accuracy', 95.0),
                'compliance_score': metrics.get('compliance_score', 5.0),
                'demand_forecast_accuracy': metrics.get('forecast_accuracy', None),
                'logistics_efficiency': metrics.get('logistics_efficiency', None),
                'data_complete': True
            }
        )
    
    def _categorize_metric(self, value, thresholds):
        """
        Categorize a metric value based on thresholds.
        
        Args:
            value (float): The metric value to categorize
            thresholds (list): List of threshold values in ascending order
            
        Returns:
            int: Category value from 1 to 5
        """
        # Default to lowest category
        category = 1
        
        # Increment category based on thresholds
        for i, threshold in enumerate(thresholds):
            if value >= threshold:
                category = i + 2
            else:
                break
                
        return category
    
    def _log_data_fetch_event(self, supplier_id, metrics):
        """
        Log a data fetching event.
        
        Args:
            supplier_id (int): ID of the supplier
            metrics (dict): The metrics that were fetched
        """
        RankingEvent.objects.create(
            event_type='DATA_FETCHED',
            description=f"Fetched performance data for supplier {supplier_id}",
            supplier_id=supplier_id,
            metadata={
                'metrics_summary': {
                    'quality': round(metrics.get('quality_score', 0), 2),
                    'delivery': round(metrics.get('on_time_delivery_rate', 0), 2),
                    'price': round(metrics.get('price_competitiveness', 0), 2),
                    'service': round(metrics.get('service_score', 0), 2)
                }
            }
        )
    
    def get_all_possible_states(self):
        """Generate all possible state combinations.

        Returns:
            list: List of all possible state objects
        """
        states = []
        
        # Create all combinations of categories
        for q in range(1, 6):
            for d in range(1, 6):
                for p in range(1, 6):
                    for s in range(1, 6):
                        state_name = f"Q{q}_D{d}_P{p}_S{s}"
                        state, created = QLearningState.objects.get_or_create(
                            name=state_name,
                            defaults={'description': f"Quality: {q}/5, Delivery: {d}/5, "
                                                f"Price: {p}/5, Service: {s}/5"}
                        )
                        states.append(state)
        
        return states