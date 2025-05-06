import os
import sys
import django
import random
from datetime import datetime, timedelta, date
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# Set up Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'supplier_ranking_service.settings')
django.setup()

# Import your local models
from api.models import (
    QLearningState, QLearningAction, QTableEntry, RankingConfiguration,
    SupplierRanking, RankingEvent
)

# Import service connectors
from connectors.user_service_connector import UserServiceConnector
from connectors.order_service_connector import OrderServiceConnector
from connectors.warehouse_service_connector import WarehouseServiceConnector

# Import your ranking components
from ranking_engine.q_learning.agent import SupplierRankingAgent
from ranking_engine.q_learning.environment import SupplierEnvironment
from ranking_engine.q_learning.state_mapper import StateMapper
from ranking_engine.services.ranking_service import RankingService
from ranking_engine.services.supplier_service import SupplierService
from ranking_engine.services.metrics_service import MetricsService
from ranking_engine.utils.data_preprocessing import preprocess_supplier_data


def setup_test_data():
    """Create test data for manual testing"""
    print("Creating test data...")
    
    # Initialize service connectors
    user_service = UserServiceConnector()
    order_service = OrderServiceConnector()
    warehouse_service = WarehouseServiceConnector()
    
    # Clear existing local data (optional)
    # QTableEntry.objects.all().delete()
    # QLearningAction.objects.all().delete()
    # QLearningState.objects.all().delete()
    # RankingConfiguration.objects.all().delete()
    # SupplierRanking.objects.all().delete()
    # RankingEvent.objects.all().delete()
    
    # For testing purposes, we'll log some information about external suppliers
    suppliers = []
    supplier_ids = [3]  # Assuming these IDs exist in User Service
    
    active_suppliers = user_service.get_active_suppliers()
    for supplier in active_suppliers:
        print("Supplier ID:", supplier["user"]["id"])
        print("Company Name:", supplier["company_name"])
    
    # Get some product information for testing
    product_ids = [101, 102, 103]  # Assuming these IDs exist in Warehouse Service
    
    for product_id in product_ids:
        suppliers_for_product = warehouse_service.get_product_suppliers(product_id)
        print(f"Product ID {product_id} has {len(suppliers_for_product)} suppliers")
    
    # Get some sample transaction data
    for supplier_id in supplier_ids[:3]:  # Just check first 3 suppliers
        performance_records = order_service.get_supplier_performance_records(supplier_id)
        print(f"Supplier ID {supplier_id} has {len(performance_records)} performance records")
    
    # Create Q-Learning states
    states = []
    state_names = [
        "high_quality_high_delivery",
        "high_quality_low_delivery",
        "low_quality_high_delivery",
        "low_quality_low_delivery",
        "medium_performance"
    ]
    
    for name in state_names:
        state = QLearningState.objects.get_or_create(
            name=name,
            defaults={'description': f"State representing {name.replace('_', ' ')}"}
        )[0]
        states.append(state)
    
    # Create Q-Learning actions
    actions = []
    action_names = [
        "increase_rank_significantly",
        "increase_rank",
        "maintain_rank",
        "decrease_rank",
        "decrease_rank_significantly"
    ]
    
    for name in action_names:
        action = QLearningAction.objects.get_or_create(
            name=name,
            defaults={'description': f"Action to {name.replace('_', ' ')}"}
        )[0]
        actions.append(action)
    
    # Create Q-Table entries with initial values
    for state in states:
        for action in actions:
            # Set initial Q-values based on intuitive actions for each state
            if "high_quality" in state.name and "increase" in action.name:
                initial_q = random.uniform(0.6, 0.9)
            elif "low_quality" in state.name and "decrease" in action.name:
                initial_q = random.uniform(0.6, 0.9)
            elif "medium" in state.name and "maintain" in action.name:
                initial_q = random.uniform(0.6, 0.9)
            else:
                initial_q = random.uniform(0.1, 0.5)
            
            QTableEntry.objects.get_or_create(
                state=state,
                action=action,
                defaults={
                    'q_value': initial_q,
                    'update_count': 0
                }
            )
    
    # Create configuration
    config = RankingConfiguration.objects.get_or_create(
        name="default",
        defaults={
            'learning_rate': 0.1,
            'discount_factor': 0.9,
            'exploration_rate': 0.2,
            'quality_weight': 0.4,
            'delivery_weight': 0.3,
            'price_weight': 0.2,
            'service_weight': 0.1,
            'is_active': True
        }
    )[0]
    
    print("Test data creation complete.")
    return supplier_ids, product_ids, config


def run_ranking_process():
    """Run the ranking process and display results"""
    from datetime import date, datetime, timedelta
    print("\nInitializing ranking components...")
    
    # Get the configuration
    config = RankingConfiguration.objects.filter(is_active=True).first()
    if not config:
        print("No active configuration found. Creating default.")
        config = RankingConfiguration.objects.create(
            name="default",
            learning_rate=0.1,
            discount_factor=0.9,
            exploration_rate=0.2,
            quality_weight=0.4,
            delivery_weight=0.3,
            price_weight=0.2,
            service_weight=0.1,
            is_active=True
        )
    
    # Initialize components
    state_mapper = StateMapper()
    environment = SupplierEnvironment()
    agent = SupplierRankingAgent(config)
    metrics_service = MetricsService()
    supplier_service = SupplierService()
    
    # Initialize service connectors for the ranking service
    user_service = UserServiceConnector()
    order_service = OrderServiceConnector()
    warehouse_service = WarehouseServiceConnector()
    
    try:
        # Create ranking service
        ranking_service = RankingService()
        
        # Run the ranking process for the current date
        today = date.today()
        print(f"Generating supplier rankings for {today}...")
        
        # Initialize service with needed components after creation
        if hasattr(ranking_service, 'set_agent'):
            ranking_service.set_agent(agent)
        if hasattr(ranking_service, 'set_environment'):
            ranking_service.set_environment(environment)
        if hasattr(ranking_service, 'set_state_mapper'):
            ranking_service.set_state_mapper(state_mapper)
        if hasattr(ranking_service, 'set_metrics_service'):
            ranking_service.set_metrics_service(metrics_service)
        if hasattr(ranking_service, 'set_supplier_service'):
            ranking_service.set_supplier_service(supplier_service)
        if hasattr(ranking_service, 'set_config'):
            ranking_service.set_config(config)
        
        # Set service connectors if they exist
        if hasattr(ranking_service, 'set_user_service'):
            ranking_service.set_user_service(user_service)
        if hasattr(ranking_service, 'set_order_service'):
            ranking_service.set_order_service(order_service)
        if hasattr(ranking_service, 'set_warehouse_service'):
            ranking_service.set_warehouse_service(warehouse_service)
        
        # Use the method that works in your implementation
        if hasattr(ranking_service, 'generate_rankings'):
            rankings = ranking_service.generate_rankings(today)
        else:
            # Fall back to what works in your integration test
            rankings = ranking_service.generate_supplier_rankings()
        
        print(f"Successfully generated {len(rankings)} rankings.")
        
        # Display the rankings
        print("\nSupplier Rankings:")
        print("-" * 80)
        print(f"{'Rank':<5}{'Supplier ID':<12}{'Supplier Name':<30}{'Overall':<10}{'Quality':<10}{'Delivery':<10}{'Price':<10}{'Service':<10}")
        print("-" * 80)
        
        for ranking in sorted(rankings, key=lambda r: r.rank):
            print(f"{ranking.rank:<5}{ranking.supplier_id:<12}{ranking.supplier_name:<30}{ranking.overall_score:<10.2f}"
                  f"{ranking.quality_score:<10.2f}{ranking.delivery_score:<10.2f}"
                  f"{ranking.price_score:<10.2f}{ranking.service_score:<10.2f}")
        
        # Run a Q-learning training iteration if the method exists
        if hasattr(ranking_service, 'update_q_values_from_transactions'):
            print("\nUpdating Q-values from recent transactions...")
            # Here we'll need to get transaction data from the order service
            # This is a placeholder - adjust according to your actual API
            recent_transactions = []
            supplier_ids = [r.supplier_id for r in rankings]
            
            for supplier_id in supplier_ids:
                start_date = today - timedelta(days=30)
                # Get transactions from order service
                supplier_transactions = order_service.get_supplier_transactions(supplier_id, start_date)
                recent_transactions.extend(supplier_transactions)
                
            ranking_service.update_q_values_from_transactions(recent_transactions)
            print(f"Updated Q-values based on {len(recent_transactions)} recent transactions.")
        
        return rankings
        
    except Exception as e:
        print(f"Error generating rankings: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def visualize_results(rankings):
    """Create visualizations of the ranking results"""
    if not rankings:
        print("No rankings to visualize.")
        return
    
    try:
        matplotlib.use('Agg')  # Use non-interactive backend if running headless
    except:
        pass
    
    # Prepare data
    supplier_ids = [r.supplier_id for r in rankings]
    supplier_names = [r.supplier_name for r in rankings]
    overall_scores = [r.overall_score for r in rankings]
    quality_scores = [r.quality_score for r in rankings]
    delivery_scores = [r.delivery_score for r in rankings]
    price_scores = [r.price_score for r in rankings]
    service_scores = [r.service_score for r in rankings]
    
    # Create bar chart of overall scores
    plt.figure(figsize=(12, 6))
    plt.bar(supplier_names, overall_scores, color='blue')
    plt.title('Overall Supplier Scores')
    plt.xlabel('Supplier')
    plt.ylabel('Score')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('overall_scores.png')
    print("Saved overall scores visualization to 'overall_scores.png'")
    
    # Create a stacked bar chart showing score components
    plt.figure(figsize=(12, 6))
    width = 0.5
    
    # Create the bars
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Create the bars
    ax.bar(supplier_names, quality_scores, width, label='Quality', color='#1f77b4')
    ax.bar(supplier_names, delivery_scores, width, bottom=quality_scores, label='Delivery', color='#ff7f0e')
    
    # Calculate position for the next stack
    bottom = [q + d for q, d in zip(quality_scores, delivery_scores)]
    ax.bar(supplier_names, price_scores, width, bottom=bottom, label='Price', color='#2ca02c')
    
    # Update bottom for the final stack
    bottom = [b + p for b, p in zip(bottom, price_scores)]
    ax.bar(supplier_names, service_scores, width, bottom=bottom, label='Service', color='#d62728')
    
    ax.set_title('Supplier Score Components')
    ax.set_xlabel('Supplier')
    ax.set_ylabel('Score')
    ax.legend(loc='upper right')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('score_components.png')
    print("Saved score components visualization to 'score_components.png'")
    
    # Create a radar chart comparing top suppliers
    if len(rankings) >= 3:
        top_suppliers = sorted(rankings, key=lambda r: r.overall_score, reverse=True)[:3]
        
        categories = ['Quality', 'Delivery', 'Price', 'Service']
        
        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, polar=True)
        
        # Number of categories
        N = len(categories)
        
        # Create angles for each category
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # Close the loop
        
        # Set the labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        
        # Plot each supplier
        colors = ['blue', 'red', 'green']
        for i, supplier in enumerate(top_suppliers):
            values = [supplier.quality_score, supplier.delivery_score, 
                      supplier.price_score, supplier.service_score]
            values += values[:1]  # Close the loop
            
            ax.plot(angles, values, linewidth=2, linestyle='solid', label=supplier.supplier_name, color=colors[i])
            ax.fill(angles, values, alpha=0.1, color=colors[i])
        
        plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
        plt.title('Top 3 Suppliers Comparison')
        plt.tight_layout()
        plt.savefig('supplier_radar.png')
        print("Saved supplier comparison radar chart to 'supplier_radar.png'")


def analyze_q_learning():
    """Analyze the Q-learning data and training progress"""
    print("\nAnalyzing Q-Learning data...")
    
    # Get all Q-table entries
    q_entries = QTableEntry.objects.all().order_by('state__name', 'action__name')
    
    if not q_entries.exists():
        print("No Q-Learning data available for analysis.")
        return
    
    # Group by state
    states = {}
    for entry in q_entries:
        if entry.state.name not in states:
            states[entry.state.name] = []
        states[entry.state.name].append({
            'action': entry.action.name,
            'q_value': entry.q_value,
            'updates': entry.update_count
        })
    
    # Print Q-table
    print("\nCurrent Q-table:")
    print("-" * 100)
    print(f"{'State':<30}{'Action':<30}{'Q-Value':<10}{'Updates':<10}")
    print("-" * 100)
    
    for state_name, actions in states.items():
        for item in actions:
            print(f"{state_name:<30}{item['action']:<30}{item['q_value']:<10.4f}{item['updates']:<10}")
    
    # Find the best action for each state
    print("\nBest actions for each state:")
    print("-" * 70)
    print(f"{'State':<30}{'Best Action':<30}{'Q-Value':<10}")
    print("-" * 70)
    
    for state_name, actions in states.items():
        best_action = max(actions, key=lambda x: x['q_value'])
        print(f"{state_name:<30}{best_action['action']:<30}{best_action['q_value']:<10.4f}")


def main():
    """Main entry point for manual testing"""
    print("=" * 80)
    print("Supplier Ranking Service Manual Test")
    print("=" * 80)
    
    # Create test data
    supplier_ids, product_ids, config = setup_test_data()
    
    # Run ranking process
    rankings = run_ranking_process()
    
    # Analyze rankings
    if rankings:
        visualize_results(rankings)
        analyze_q_learning()
    
    print("\nManual test completed.")


if __name__ == "__main__":
    main()