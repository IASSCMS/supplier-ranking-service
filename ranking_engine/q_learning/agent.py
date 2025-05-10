"""
Agent module for Q-Learning implementation.

This module implements the Q-Learning agent that learns to rank suppliers
based on their performance metrics.
"""

from api.models import (
    QLearningState, QLearningAction, QTableEntry,
    SupplierRanking, RankingConfiguration
)
from ranking_engine.q_learning.environment import SupplierEnvironment
from connectors.group29_connector import Group29Connector
from connectors.group30_connector import Group30Connector
from connectors.group32_connector import Group32Connector
from ranking_engine.services.supplier_service import SupplierService
from ranking_engine.services.metrics_service import MetricsService
import random
import numpy as np
import logging

logger = logging.getLogger(__name__)


class SupplierRankingAgent:
    """
    Q-Learning agent for supplier ranking.
    
    This class implements the Q-Learning algorithm to learn optimal
    supplier ranking policies based on performance metrics.
    """
    
    def __init__(self, config=None):
        """
        Initialize the Q-Learning agent.
        
        Args:
            config (RankingConfiguration, optional): Configuration for the agent
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
        
        # Initialize Q-Learning parameters
        self.learning_rate = self.config.learning_rate
        self.discount_factor = self.config.discount_factor
        self.exploration_rate = self.config.exploration_rate
        
        # Initialize environment
        self.environment = SupplierEnvironment(config=self.config)
        
        # Initialize service connectors
        self.supplier_service = SupplierService()
        self.metrics_service = MetricsService()
        self.demand_forecast_connector = Group29Connector()
        self.blockchain_connector = Group30Connector()
        self.logistics_connector = Group32Connector()
    
    def select_action(self, state, available_actions=None, exploration=True):
        """
        Select an action using epsilon-greedy policy.
        
        Args:
            state (QLearningState): Current state
            available_actions (list, optional): List of available actions
            exploration (bool): Whether to use exploration
            
        Returns:
            QLearningAction: Selected action
        """
        # Get available actions if not provided
        if available_actions is None:
            available_actions = self.environment.get_actions(state)
        
        # Exploration: random action
        if exploration and random.random() < self.exploration_rate:
            return random.choice(available_actions)
        
        # Exploitation: best action based on Q-values
        q_values = []
        
        for action in available_actions:
            # Get Q-value for state-action pair
            q_entry, created = QTableEntry.objects.get_or_create(
                state=state,
                action=action,
                defaults={'q_value': 0.0}
            )
            q_values.append((action, q_entry.q_value))
        
        # Find action with maximum Q-value
        if q_values:
            # In case of ties, randomly select among the best actions
            max_q = max(q_values, key=lambda x: x[1])[1]
            best_actions = [action for action, q_value in q_values if q_value == max_q]
            return random.choice(best_actions)
        else:
            # If no Q-values, select random action
            return random.choice(available_actions)
    
    def learn(self, state, action, reward, next_state):
        """
        Update Q-value for a state-action pair based on reward and next state.
        
        Args:
            state (QLearningState): Current state
            action (QLearningAction): Action taken
            reward (float): Reward received
            next_state (QLearningState): Next state
            
        Returns:
            float: Updated Q-value
        """
        # Get current Q-value
        q_entry, created = QTableEntry.objects.get_or_create(
            state=state,
            action=action,
            defaults={'q_value': 0.0}
        )
        current_q = q_entry.q_value
        
        # Get maximum Q-value for next state
        next_actions = self.environment.get_actions(next_state)
        next_q_values = []
        
        for next_action in next_actions:
            next_q_entry, created = QTableEntry.objects.get_or_create(
                state=next_state,
                action=next_action,
                defaults={'q_value': 0.0}
            )
            next_q_values.append(next_q_entry.q_value)
        
        max_next_q = max(next_q_values) if next_q_values else 0.0
        
        # Update Q-value using Q-learning formula
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        # Update Q-value in database
        q_entry.q_value = new_q
        q_entry.update_count += 1
        q_entry.save()
        
        return new_q
    
    def rank_supplier(self, supplier_id, update_ranking=True, exploration=True):
        """
        Rank a supplier using the learned Q-values.
        
        Args:
            supplier_id (int): ID of the supplier
            update_ranking (bool): Whether to update the ranking in database
            exploration (bool): Whether to use exploration
            
        Returns:
            tuple: (action, reward, ranking)
        """
        try:
            # Get supplier from supplier service
            supplier = self.supplier_service.get_supplier(supplier_id)
            
            if not supplier:
                logger.error(f"Supplier with ID {supplier_id} does not exist or could not be fetched")
                return None, 0.0, None
                
            # Get current state
            current_state = self.environment.get_state(supplier_id)
            
            # Select action
            selected_action = self.select_action(current_state, exploration=exploration)
            
            # Get reward
            reward = self.environment.get_reward(supplier_id, current_state, selected_action)
            
            # Get next state
            next_state = self.environment.next_state(supplier_id, selected_action)
            
            # Update Q-value
            self.learn(current_state, selected_action, reward, next_state)
            
            # Update ranking in database if requested
            ranking = None
            if update_ranking:
                ranking = self.environment.update_rankings(supplier_id, selected_action)
            
            return selected_action, reward, ranking
            
        except Exception as e:
            logger.error(f"Error ranking supplier {supplier_id}: {str(e)}")
            return None, 0.0, None
    
    def batch_train(self, iterations=100, supplier_ids=None):
        """
        Train the agent on a batch of suppliers.
        
        Args:
            iterations (int): Number of training iterations
            supplier_ids (list, optional): List of supplier IDs to train on
        """
        if supplier_ids is None:
            # Get all suppliers and extract IDs, handling both direct id and nested user.id structures
            suppliers = self.supplier_service.get_all_suppliers()
            supplier_ids = []
            for supplier in suppliers:
                # Check if id is directly available or nested in user dictionary
                if 'id' in supplier:
                    supplier_ids.append(supplier['id'])
                elif 'user' in supplier and 'id' in supplier['user']:
                    supplier_ids.append(supplier['user']['id'])
        
        for _ in range(iterations):
            for supplier_id in supplier_ids:
                self.rank_supplier(supplier_id, update_ranking=False, exploration=True)
    
    def get_q_table(self, supplier_id=None):
        """
        Get the Q-table for a specific supplier or all suppliers.
        
        Args:
            supplier_id (int, optional): ID of the supplier
            
        Returns:
            dict: Q-table entries
        """
        if supplier_id:
            state = self.environment.get_state(supplier_id)
            actions = self.environment.get_actions(state)
            q_entries = QTableEntry.objects.filter(state=state, action__in=actions)
        else:
            q_entries = QTableEntry.objects.all()
        
        return {f"{entry.state.name} - {entry.action.name}": entry.q_value for entry in q_entries}
    
    def get_policy(self, supplier_id=None):
        """
        Get the current policy for a specific supplier or all suppliers.
        
        Args:
            supplier_id (int, optional): ID of the supplier
            
        Returns:
            dict: Policy entries
        """
        if supplier_id:
            state = self.environment.get_state(supplier_id)
            actions = self.environment.get_actions(state)
            q_entries = QTableEntry.objects.filter(state=state, action__in=actions)
        else:
            q_entries = QTableEntry.objects.all()
        
        policy = {}
        for entry in q_entries:
            if entry.state.name not in policy:
                policy[entry.state.name] = {}
            policy[entry.state.name][entry.action.name] = entry.q_value
        
        return policy
    
    def rank_all_suppliers(self, exploration=False):
        """
        Rank all suppliers using the learned Q-values.
        
        Args:
            exploration (bool): Whether to use exploration
            
        Returns:
            list: List of ranking objects
        """
        # Get all suppliers and extract IDs, handling both direct id and nested user.id structures
        suppliers = self.supplier_service.get_all_suppliers()
        supplier_ids = []
        for supplier in suppliers:
            # Check if id is directly available or nested in user dictionary
            if 'id' in supplier:
                supplier_ids.append(supplier['id'])
            elif 'user' in supplier and 'id' in supplier['user']:
                supplier_ids.append(supplier['user']['id'])
        
        rankings = []
        
        for supplier_id in supplier_ids:
            action, reward, ranking = self.rank_supplier(supplier_id, update_ranking=True, exploration=exploration)
            if ranking:
                rankings.append(ranking)
        
        return rankings
    
    def reset_q_table(self):
        """Reset the Q-table to initial values."""
        QTableEntry.objects.all().update(q_value=0.0, update_count=0)
    
    def get_best_action(self, state):
        """
        Get the best action for a given state.
        
        Args:
            state (QLearningState): Current state
            
        Returns:
            QLearningAction: Best action
        """
        available_actions = self.environment.get_actions(state)
        return self.select_action(state, available_actions, exploration=False)
    
    def update_q_table(self, state, action, reward, next_state=None):
        """
        Update the Q-value for a state-action pair based on the reward.
        
        Args:
            state (str or QLearningState): Current state name or object
            action (str or QLearningAction): Action name or object
            reward (float): Reward received
            next_state (str or QLearningState, optional): Next state name or object
        """
        # Convert string state name to QLearningState object if needed
        if isinstance(state, str):
            state_obj, created = QLearningState.objects.get_or_create(
                name=state,
                defaults={'description': f'Auto-created state: {state}'}
            )
            state = state_obj
            
        # Convert string action name to QLearningAction object if needed
        if isinstance(action, str):
            action_obj, created = QLearningAction.objects.get_or_create(
                name=action,
                defaults={'description': f'Auto-created action: {action}'}
            )
            action = action_obj
            
        # Convert next_state if provided
        if next_state is not None and isinstance(next_state, str):
            next_state_obj, created = QLearningState.objects.get_or_create(
                name=next_state,
                defaults={'description': f'Auto-created state: {next_state}'}
            )
            next_state = next_state_obj
            
        # Now call learn with proper objects
        self.learn(state, action, reward, next_state)