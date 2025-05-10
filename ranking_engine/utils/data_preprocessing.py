"""
Utility functions for preprocessing supplier data for the Q-Learning algorithm.
This module handles data normalization, feature extraction, and preparation
of supplier performance metrics for use in the ranking system.
"""
import pandas as pd
import numpy as np
from django.db.models import Avg, Count, F, Sum, Max, Min
from django.utils import timezone
from collections import defaultdict
from datetime import timedelta
from api.models import (
    QLearningState, QLearningAction, QTableEntry, 
    SupplierRanking, SupplierPerformanceCache, RankingConfiguration
)
from connectors.user_service_connector import UserServiceConnector
from connectors.order_service_connector import OrderServiceConnector
from connectors.warehouse_service_connector import WarehouseServiceConnector

def get_supplier_info(supplier_id):
    """
    Get detailed information about a specific supplier
    
    Args:
        supplier_id (int): ID of the supplier
        
    Returns:
        dict: Supplier details including compliance score
    """
    connector = UserServiceConnector()
    return connector.get_supplier_info(supplier_id)

def get_all_active_suppliers():
    """
    Get all active suppliers from the User Service
    
    Returns:
        list: List of active supplier dictionaries
    """
    connector = UserServiceConnector()
    return connector.get_active_suppliers()

def get_transactions(supplier_id=None, start_date=None, end_date=None):
    """
    Get transactions from Order Management Service
    
    Args:
        supplier_id (int, optional): Filter by supplier ID
        start_date (date, optional): Filter by start date
        end_date (date, optional): Filter by end date
        
    Returns:
        list: List of transaction dictionaries
    """
    connector = OrderServiceConnector()
    return connector.get_supplier_transactions(supplier_id, start_date)

def get_supplier_products(supplier_id):
    """
    Get products offered by a specific supplier
    
    Args:
        supplier_id (int): ID of the supplier
        
    Returns:
        list: List of product dictionaries
    """
    connector = WarehouseServiceConnector()
    return connector.get_supplier_products(supplier_id)

def preprocess_supplier_data(transactions):
    """
    Preprocess transaction data to extract metrics for each supplier.
    
    Args:
        transactions: List of Transaction objects from Order Management Service
        
    Returns:
        Dictionary with supplier IDs as keys and dictionaries of metrics as values
    """
    # Initialize data structure to hold metrics for each supplier
    supplier_data = defaultdict(lambda: {
        'total_items': 0,
        'defect_items': 0,
        'total_orders': 0,
        'on_time_orders': 0,
        'late_orders': 0,
        'total_delay_days': 0,
        'total_amount': 0,  # Initialize as int/float compatible with Decimal
    })
    
    # Process each transaction
    for transaction in transactions:
        supplier_id = transaction.get('supplier_id')
        
        # Add transaction data to supplier metrics
        supplier_data[supplier_id]['total_items'] += transaction.get('quantity', 0)
        supplier_data[supplier_id]['defect_items'] += transaction.get('defect_count', 0)
        supplier_data[supplier_id]['total_orders'] += 1
        
        # Convert both operands to same type before multiplication
        # This fixes the type mismatch between float and Decimal
        unit_price = float(transaction.get('unit_price', 0))
        transaction_amount = transaction.get('quantity', 0) * unit_price
        supplier_data[supplier_id]['total_amount'] += transaction_amount
        
        # Calculate delivery performance
        actual_delivery_date = transaction.get('actual_delivery_date')
        expected_delivery_date = transaction.get('expected_delivery_date')
        
        if actual_delivery_date and expected_delivery_date:
            if actual_delivery_date <= expected_delivery_date:
                supplier_data[supplier_id]['on_time_orders'] += 1
            else:
                supplier_data[supplier_id]['late_orders'] += 1
                delay = (actual_delivery_date - expected_delivery_date).days
                supplier_data[supplier_id]['total_delay_days'] += delay
    
    # Calculate derived metrics for each supplier
    result = {}
    for supplier_id, data in supplier_data.items():
        metrics = {}
        
        # Calculate defect rate (percentage of defective items)
        if data['total_items'] > 0:
            metrics['defect_rate'] = (data['defect_items'] / data['total_items']) * 100
        else:
            metrics['defect_rate'] = 0.0
        
        # Calculate on-time delivery rate
        if data['total_orders'] > 0:
            metrics['on_time_delivery_rate'] = (data['on_time_orders'] / data['total_orders']) * 100
        else:
            metrics['on_time_delivery_rate'] = 0.0
        
        # Calculate average delay for late deliveries
        if data['late_orders'] > 0:
            metrics['average_delay_days'] = data['total_delay_days'] / data['late_orders']
        else:
            metrics['average_delay_days'] = 0.0
        
        # Add original data for reference
        metrics.update(data)
        
        result[supplier_id] = metrics
    
    return result

def normalize_metric(value, min_val, max_val, reverse=False):
    """
    Normalize a metric to a value between 0 and 1.
    
    Args:
        value: The value to normalize
        min_val: The minimum value in the dataset
        max_val: The maximum value in the dataset
        reverse: If True, smaller values are better (e.g., defect rate)
        
    Returns:
        Normalized value between 0 and 1
    """
    if min_val == max_val:
        return 0.5  # Default when there's no variation
    
    if reverse:
        # For metrics where lower is better
        return 1 - ((value - min_val) / (max_val - min_val)) if max_val > min_val else 0.5
    else:
        # For metrics where higher is better
        return (value - min_val) / (max_val - min_val) if max_val > min_val else 0.5

def calculate_supplier_metrics(supplier_id, start_date=None, end_date=None):
    """
    Calculate comprehensive metrics for a specific supplier within a date range.
    
    Args:
        supplier_id: ID of the supplier
        start_date: Beginning of the date range (default: 90 days ago)
        end_date: End of the date range (default: today)
        
    Returns:
        Dictionary containing calculated metrics
    """
    if not start_date:
        start_date = timezone.now().date() - timedelta(days=90)
    if not end_date:
        end_date = timezone.now().date()
        
    # Get supplier details from User Service
    supplier = get_supplier_info(supplier_id)
    if not supplier:
        return None
    
    # Get performance records from cache in date range
    performance_records = SupplierPerformanceCache.objects.filter(
        supplier_id=supplier_id,
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Get transactions from Order Management Service in date range
    transactions = get_transactions(
        supplier_id=supplier_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # If no data, return empty metrics
    if not performance_records.exists() and not transactions:
        return {
            'supplier_id': supplier_id,
            'supplier_name': supplier.get('name', f'Supplier {supplier_id}'),
            'data_available': False,
            'message': 'No data available for this supplier in the specified date range'
        }
    
    # Calculate average performance metrics if records exist
    performance_metrics = {}
    if performance_records.exists():
        performance_agg = performance_records.aggregate(
            avg_quality_score=Avg('quality_score'),
            avg_defect_rate=Avg('defect_rate'),
            avg_return_rate=Avg('return_rate'),
            avg_on_time_delivery_rate=Avg('on_time_delivery_rate'),
            avg_delay_days=Avg('average_delay_days'),
            avg_price_competitiveness=Avg('price_competitiveness'),
            avg_responsiveness=Avg('responsiveness'),
            avg_issue_resolution_time=Avg('issue_resolution_time'),
            avg_fill_rate=Avg('fill_rate'),
            avg_order_accuracy=Avg('order_accuracy'),
            avg_compliance_score=Avg('compliance_score')
        )
        performance_metrics = performance_agg
    
    # Calculate transaction-based metrics if transactions exist
    transaction_metrics = {}
    if transactions:
        # Filter delivered transactions
        delivered_transactions = [t for t in transactions if t.get('status') == 'DELIVERED' and t.get('actual_delivery_date')]
        
        # Calculate delivery metrics
        if delivered_transactions:
            on_time_count = sum(1 for t in delivered_transactions 
                               if t.get('actual_delivery_date') <= t.get('expected_delivery_date'))
            
            total_delivered = len(delivered_transactions)
            on_time_percentage = (on_time_count / total_delivered * 100) if total_delivered > 0 else 0
            
            late_deliveries = [t for t in delivered_transactions 
                              if t.get('actual_delivery_date') > t.get('expected_delivery_date')]
            
            total_delay_days = sum((t.get('actual_delivery_date') - t.get('expected_delivery_date')).days 
                                   for t in late_deliveries)
            
            avg_delay_days = total_delay_days / len(late_deliveries) if late_deliveries else 0
            
            transaction_metrics['transaction_on_time_rate'] = on_time_percentage
            transaction_metrics['transaction_avg_delay_days'] = avg_delay_days
        
        # Calculate quality metrics
        total_quantity = sum(t.get('quantity', 0) for t in transactions)
        total_defects = sum(t.get('defect_count', 0) for t in transactions)
        
        if total_quantity > 0:
            defect_rate = (total_defects / total_quantity * 100)
            transaction_metrics['transaction_defect_rate'] = defect_rate
        
        # Calculate cancellation rate
        cancelled_count = sum(1 for t in transactions if t.get('status') == 'CANCELLED')
        total_transactions = len(transactions)
        
        if total_transactions > 0:
            cancellation_rate = (cancelled_count / total_transactions * 100)
            transaction_metrics['cancellation_rate'] = cancellation_rate
    
    # Combine all metrics
    result = {
        'supplier_id': supplier_id,
        'supplier_name': supplier.get('company_name', f'Supplier {supplier_id}'),
        'data_available': True,
        'metrics_period': {
            'start_date': start_date,
            'end_date': end_date
        }
    }
    
    # Add supplier basic info from User Service
    result.update({
        'credit_score': supplier.get('credit_score'),
        'average_lead_time': supplier.get('average_lead_time'),
        'supplier_size': supplier.get('supplier_size'),
        'is_active': supplier.get('is_active', True),
    })
    
    # Add performance metrics if available
    if performance_metrics:
        result.update(performance_metrics)
    
    # Add transaction metrics if available
    if transaction_metrics:
        result.update(transaction_metrics)
    
    return result

def extract_features_for_q_learning(supplier_id, metrics=None):
    """
    Extract and transform supplier metrics into features for Q-Learning.
    
    Args:
        supplier_id: ID of the supplier
        metrics: Pre-calculated metrics (optional, will be calculated if not provided)
        
    Returns:
        Dictionary of features suitable for Q-Learning state mapping
    """
    if not metrics:
        metrics = calculate_supplier_metrics(supplier_id)
    
    if not metrics or not metrics.get('data_available', False):
        return None
    
    # Get all active suppliers for normalization context
    all_suppliers = get_all_active_suppliers()
    supplier_ids = [s['user'].get('id') for s in all_suppliers]
    
    # If there's only one supplier, we can't normalize properly
    if len(supplier_ids) <= 1:
        return {
            'supplier_id': supplier_id,
            'quality_score': 0.5,
            'delivery_score': 0.5,
            'price_score': 0.5,
            'responsiveness_score': 0.5,
            'risk_score': 0.5
        }
    
    # Get min/max values for normalization using performance cache
    # For quality metrics
    quality_bounds = SupplierPerformanceCache.objects.filter(
        supplier_id__in=supplier_ids
    ).aggregate(
        min_quality=Min('quality_score'),
        max_quality=Max('quality_score'),
        min_defect=Min('defect_rate'),
        max_defect=Max('defect_rate')
    )
    
    # For delivery metrics
    delivery_bounds = SupplierPerformanceCache.objects.filter(
        supplier_id__in=supplier_ids
    ).aggregate(
        min_otd=Min('on_time_delivery_rate'),
        max_otd=Max('on_time_delivery_rate'),
        min_delay=Min('average_delay_days'),
        max_delay=Max('average_delay_days')
    )
    
    # For price metrics
    price_bounds = SupplierPerformanceCache.objects.filter(
        supplier_id__in=supplier_ids
    ).aggregate(
        min_price=Min('price_competitiveness'),
        max_price=Max('price_competitiveness')
    )
    
    # Extract and normalize features
    features = {
        'supplier_id': supplier_id,
    }
    
    # Quality feature
    quality_score = metrics.get('avg_quality_score', 5.0)
    defect_rate = metrics.get('avg_defect_rate', 2.0)
    
    norm_quality = normalize_metric(
        quality_score,
        quality_bounds.get('min_quality', 0),
        quality_bounds.get('max_quality', 10)
    )
    
    norm_defect = normalize_metric(
        defect_rate,
        quality_bounds.get('min_defect', 0),
        quality_bounds.get('max_defect', 100),
        reverse=True  # Lower defect rate is better
    )
    
    features['quality_score'] = (norm_quality + norm_defect) / 2
    
    # Delivery feature
    on_time_rate = metrics.get('avg_on_time_delivery_rate', 50.0)
    delay_days = metrics.get('avg_delay_days', 2.0)
    
    norm_otd = normalize_metric(
        on_time_rate,
        delivery_bounds.get('min_otd', 0),
        delivery_bounds.get('max_otd', 100)
    )
    
    norm_delay = normalize_metric(
        delay_days,
        delivery_bounds.get('min_delay', 0),
        delivery_bounds.get('max_delay', 10),
        reverse=True  # Lower delay is better
    )
    
    features['delivery_score'] = (norm_otd + norm_delay) / 2
    
    # Price feature
    price_comp = metrics.get('avg_price_competitiveness', 5.0)
    
    features['price_score'] = normalize_metric(
        price_comp,
        price_bounds.get('min_price', 0),
        price_bounds.get('max_price', 10)
    )
    
    # Responsiveness feature (service)
    resp_score = metrics.get('avg_responsiveness', 5.0)
    features['responsiveness_score'] = resp_score / 10.0  # Assuming 0-10 scale
    
    # Risk score (based on credit score, cancellation rate, etc.)
    credit_score = metrics.get('credit_score', 50.0)
    cancellation_rate = metrics.get('cancellation_rate', 5.0)
    
    # Normalize and combine for risk (lower is better for risk)
    norm_credit = credit_score / 100.0 if credit_score else 0.5
    norm_cancel = 1.0 - (cancellation_rate / 100.0) if cancellation_rate else 0.5
    
    features['risk_score'] = (norm_credit + norm_cancel) / 2
    
    return features

def discretize_features(features, num_buckets=5):
    """
    Convert continuous feature values to discrete buckets for Q-Learning states.
    
    Args:
        features: Dictionary of normalized features
        num_buckets: Number of buckets to divide the feature range into
        
    Returns:
        Dictionary of discretized features
    """
    discretized = {}
    
    for key, value in features.items():
        if key == 'supplier_id':
            discretized[key] = value
            continue
            
        if value is None:
            discretized[key] = 'medium'  # Default for missing values
            continue
            
        # Divide 0-1 range into buckets
        bucket_size = 1.0 / num_buckets
        bucket = min(int(value / bucket_size), num_buckets - 1)
        
        # Convert bucket to text label
        if num_buckets == 3:
            labels = ['low', 'medium', 'high']
        elif num_buckets == 5:
            labels = ['very_low', 'low', 'medium', 'high', 'very_high']
        else:
            labels = [str(i) for i in range(num_buckets)]
            
        discretized[key] = labels[bucket]
    
    return discretized

def create_state_key(discretized_features):
    """
    Create a state key string from discretized features for Q-Learning.
    
    Args:
        discretized_features: Dictionary of discretized features
        
    Returns:
        String representing the state
    """
    # Order of features in state key
    feature_order = [
        'quality_score', 'delivery_score', 'price_score', 
        'responsiveness_score', 'risk_score'
    ]
    
    # Create state key
    state_parts = []
    for feature in feature_order:
        if feature in discretized_features:
            state_parts.append(f"{feature}_{discretized_features[feature]}")
    
    return "_".join(state_parts)

def prepare_supplier_data_for_ranking(supplier_ids=None, days=90):
    """
    Prepare data for all suppliers (or specified suppliers) for ranking.
    
    Args:
        supplier_ids: List of supplier IDs (default: all active suppliers)
        days: Number of days to look back for data
        
    Returns:
        List of dictionaries with supplier features
    """
    if not supplier_ids:
        # Get active suppliers
        suppliers = get_all_active_suppliers()
        supplier_ids = [s['user'].get('id') for s in suppliers]
    
    start_date = timezone.now().date() - timedelta(days=days)
    end_date = timezone.now().date()
    
    result = []
    for supplier_id in supplier_ids:
        # Calculate metrics
        metrics = calculate_supplier_metrics(supplier_id, start_date, end_date)
        
        if not metrics or not metrics.get('data_available', False):
            continue
        
        # Extract features
        features = extract_features_for_q_learning(supplier_id, metrics)
        
        if features:
            # Add original metrics for reference
            features['raw_metrics'] = metrics
            result.append(features)
    
    return result

def get_data_from_other_groups():
    """
    Fetch data from other groups' services.
    
    Returns:
        Dictionary with data from other groups
    """
    # Import the connectors for each group
    from connectors.group29_connector import Group29Connector
    from connectors.group30_connector import Group30Connector
    from connectors.group32_connector import Group32Connector
    
    # Fetch data from each service
    group29_data = Group29Connector()
    group30_data = Group30Connector()
    group32_data = Group32Connector()
    
    return {
        'group29_data': group29_data,  # Demand forecasting data
        'group30_data': group30_data,  # Blockchain tracking data
        'group32_data': group32_data,  # Logistics optimization data
    }