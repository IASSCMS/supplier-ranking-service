"""
Metrics Service - Calculates and aggregates supplier performance metrics

This service handles the calculation of all metrics used to evaluate
supplier performance, which will feed into the Q-Learning ranking system.
"""

from django.utils import timezone
from datetime import date, timedelta
import numpy as np

from api.models import (
    SupplierPerformanceCache,
    RankingConfiguration
)
from connectors.user_service_connector import UserServiceConnector
from connectors.warehouse_service_connector import WarehouseServiceConnector
from connectors.order_service_connector import OrderServiceConnector


class MetricsService:
    """Service for calculating supplier performance metrics"""
    
    def __init__(self):
        """Initialize connections to external services"""
        self.user_service = UserServiceConnector()
        self.warehouse_service = WarehouseServiceConnector()
        self.order_service = OrderServiceConnector()
    
    @staticmethod
    def get_active_configuration():
        """
        Returns the active ranking configuration
        """
        try:
            return RankingConfiguration.objects.get(is_active=True)
        except RankingConfiguration.DoesNotExist:
            # Return default configuration if none exists
            return RankingConfiguration(
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
    
    def calculate_quality_metrics(self, supplier_id, days=90):
        """
        Calculates quality-related metrics for a supplier
        
        Returns:
            dict: Dictionary containing quality metrics
        """
        start_date = timezone.now() - timedelta(days=days)
        
        # Get transactions from Order Service
        transactions = self.order_service.get_supplier_transactions(
            supplier_id=supplier_id,
            start_date=start_date
        )
        
        # Get performance records from Order Service
        performance_records = self.order_service.get_supplier_performance_records(
            supplier_id=supplier_id,
            start_date=start_date
        )
        
        # Calculate quality metrics from transactions
        total_orders = len(transactions)
        total_quantity = sum(transaction.get('quantity', 0) for transaction in transactions)
        total_defects = sum(transaction.get('defect_count', 0) for transaction in transactions)
        
        # Calculate defect rate
        defect_rate = (total_defects / total_quantity * 100) if total_quantity > 0 else 0
        
        # Calculate return rate (transactions marked as RETURNED)
        returned_transactions = [t for t in transactions if t.get('status') == 'RETURNED']
        return_rate = (len(returned_transactions) / total_orders * 100) if total_orders > 0 else 0
        
        # Average quality scores from performance records
        quality_scores = [record.get('quality_score', 0) for record in performance_records]
        defect_rates = [record.get('defect_rate', 0) for record in performance_records]
        return_rates = [record.get('return_rate', 0) for record in performance_records]
        
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        avg_recorded_defect_rate = sum(defect_rates) / len(defect_rates) if defect_rates else 0
        avg_recorded_return_rate = sum(return_rates) / len(return_rates) if return_rates else 0
        
        # Combine transaction-based metrics with recorded metrics
        # using weightings that favor recent transaction data
        combined_defect_rate = defect_rate * 0.7 + avg_recorded_defect_rate * 0.3
        combined_return_rate = return_rate * 0.7 + avg_recorded_return_rate * 0.3
        
        # Convert to a 0-10 scale for consistency
        defect_rate_score = max(0, 10 - (combined_defect_rate / 2))
        return_rate_score = max(0, 10 - (combined_return_rate / 2))
        
        # Weighted quality score (can be adjusted based on business needs)
        quality_score = (
            avg_quality_score * 0.4 +
            defect_rate_score * 0.4 +
            return_rate_score * 0.2
        )
        
        return {
            'quality_score': quality_score,
            'defect_rate': combined_defect_rate,
            'return_rate': combined_return_rate,
            'raw_quality_score': avg_quality_score,
            'transactions_analyzed': total_orders,
            'quantity_analyzed': total_quantity
        }
    
    def calculate_delivery_metrics(self, supplier_id, days=90):
        """
        Calculates delivery-related metrics for a supplier
        
        Returns:
            dict: Dictionary containing delivery metrics
        """
        from datetime import datetime
        
        start_date = date.today() - timedelta(days=days)
        
        # Get transactions from Order Service
        transactions = self.order_service.get_supplier_transactions(
            supplier_id=supplier_id,
            start_date=start_date
        )
        
        # Get performance records
        performance_records = self.order_service.get_supplier_performance_records(
            supplier_id=supplier_id,
            start_date=start_date
        )
        
        # Focus on completed transactions
        completed_transactions = [
            t for t in transactions 
            if t.get('status') == 'completed' and t.get('actual_delivery_date')
        ]
        
        # Calculate on-time delivery rate
        total_delivered = len(completed_transactions)
        
        if total_delivered > 0:
            on_time_delivered = len([
                t for t in completed_transactions
                if (t.get('actual_delivery_date') and t.get('expected_delivery_date') and
                    t.get('actual_delivery_date') <= t.get('expected_delivery_date'))
            ])
        else:
            on_time_delivered = 0
            
        on_time_rate = (on_time_delivered / total_delivered * 100) if total_delivered > 0 else 0
        
        # Calculate average delay in days for delayed transactions
        delayed_transactions = [
            t for t in completed_transactions
            if t.get('actual_delivery_date') and t.get('expected_delivery_date') and
            t.get('actual_delivery_date') > t.get('expected_delivery_date')
        ]
        
        if delayed_transactions:
            # Parse date strings to datetime objects before subtraction
            total_delay_days = sum(
                (datetime.strptime(t.get('actual_delivery_date'), '%Y-%m-%d') - 
                 datetime.strptime(t.get('expected_delivery_date'), '%Y-%m-%d')).days
                for t in delayed_transactions
            )
            avg_delay = total_delay_days / len(delayed_transactions)
        else:
            avg_delay = 0
        
        # Get averages from performance records
        on_time_rates = [record.get('on_time_delivery_rate', 0) for record in performance_records]
        delay_days = [record.get('average_delay_days', 0) for record in performance_records]
        
        avg_recorded_on_time_rate = sum(on_time_rates) / len(on_time_rates) if on_time_rates else 0
        avg_recorded_delay = sum(delay_days) / len(delay_days) if delay_days else 0
        
        # Combine transaction-based metrics with recorded metrics
        combined_on_time_rate = on_time_rate * 0.7 + avg_recorded_on_time_rate * 0.3
        combined_avg_delay = avg_delay * 0.7 + avg_recorded_delay * 0.3
        
        # Convert to a 0-10 scale score
        on_time_score = combined_on_time_rate / 10
        delay_score = max(0, 10 - min(10, combined_avg_delay * 2))
        
        # Get fill rate and order accuracy from performance records
        fill_rates = [record.get('fill_rate', 90.0) for record in performance_records]
        order_accuracies = [record.get('order_accuracy', 95.0) for record in performance_records]
        
        avg_fill_rate = sum(fill_rates) / len(fill_rates) if fill_rates else 90.0
        avg_order_accuracy = sum(order_accuracies) / len(order_accuracies) if order_accuracies else 95.0
        
        # Weighted delivery score
        delivery_score = (
            on_time_score * 0.6 +
            delay_score * 0.4
        )
        
        return {
            'delivery_score': delivery_score,
            'on_time_delivery_rate': combined_on_time_rate,
            'average_delay_days': combined_avg_delay,
            'fill_rate': avg_fill_rate,
            'order_accuracy': avg_order_accuracy,
            'transactions_analyzed': total_delivered
        }
    
    def calculate_price_metrics(self, supplier_id, days=90):
        """
        Calculates price-related metrics for a supplier
        
        Returns:
            dict: Dictionary containing price metrics
        """
        start_date = date.today() - timedelta(days=days)
        
        # Get performance records from Order Service
        performance_records = self.order_service.get_supplier_performance_records(
            supplier_id=supplier_id,
            start_date=start_date
        )
        
        # Get average price competitiveness from performance records
        price_comp_scores = [record.get('price_competitiveness', 5.0) for record in performance_records]
        avg_price_comp = sum(price_comp_scores) / len(price_comp_scores) if price_comp_scores else 5.0
        
        # Get supplier products from Warehouse Service
        supplier_products = self.warehouse_service.get_supplier_products(supplier_id)
        
        # Get all products this supplier offers
        product_ids = [sp.get('product_id') for sp in supplier_products]
        
        # Calculate price competitiveness for each product by comparing with other suppliers
        product_price_scores = []
        
        for product_id in product_ids:
            # Get this supplier's price for the product
            current_supplier_product = next(
                (sp for sp in supplier_products if sp.get('product_id') == product_id), 
                None
            )
            
            if not current_supplier_product:
                continue
                
            current_price = current_supplier_product.get('unit_price')
            
            # Get all suppliers for this product
            all_supplier_products = self.warehouse_service.get_product_suppliers(product_id)
            all_prices = [sp.get('unit_price') for sp in all_supplier_products]
            
            if all_prices:
                # Calculate percentile rank (lower is better for price)
                if len(all_prices) > 1:
                    sorted_prices = sorted(all_prices)
                    
                    # Find the position where this price would be inserted
                    import bisect
                    position = bisect.bisect_left(sorted_prices, current_price)
                    
                    # Calculate percentile based on position
                    percentile = position / (len(sorted_prices) - 1) if len(sorted_prices) > 1 else 0.5
                    
                    # Convert to a 0-10 score (10 being the cheapest)
                    price_score = 10 * (1 - percentile)
                else:
                    price_score = 5.0  # Default if this is the only supplier
                
                product_price_scores.append(price_score)
        
        # Calculate overall price score
        calculated_price_score = (
            np.mean(product_price_scores) if product_price_scores else 5.0
        )
        
        # Combine calculated score with recorded competitiveness
        price_score = calculated_price_score * 0.7 + avg_price_comp * 0.3
        
        return {
            'price_score': price_score,
            'price_competitiveness': avg_price_comp,
            'calculated_price_competitiveness': calculated_price_score,
            'products_analyzed': len(product_price_scores)
        }
    
    def calculate_service_metrics(self, supplier_id, days=90):
        """
        Calculates service-related metrics for a supplier
        
        Returns:
            dict: Dictionary containing service metrics
        """
        start_date = date.today() - timedelta(days=days)
        
        # Get performance records from Order Service
        performance_records = self.order_service.get_supplier_performance_records(
            supplier_id=supplier_id,
            start_date=start_date
        )
        
        # Get service metrics from performance records
        responsiveness_scores = [record.get('responsiveness', 5.0) for record in performance_records]
        issue_resolution_times = [record.get('issue_resolution_time') for record in performance_records 
                                if record.get('issue_resolution_time') is not None]
        fill_rates = [record.get('fill_rate', 90.0) for record in performance_records]
        order_accuracies = [record.get('order_accuracy', 95.0) for record in performance_records]
        
        avg_responsiveness = sum(responsiveness_scores) / len(responsiveness_scores) if responsiveness_scores else 5.0
        avg_fill_rate = sum(fill_rates) / len(fill_rates) if fill_rates else 90.0
        avg_order_accuracy = sum(order_accuracies) / len(order_accuracies) if order_accuracies else 95.0
        
        if issue_resolution_times:
            avg_issue_resolution = sum(issue_resolution_times) / len(issue_resolution_times)
        else:
            avg_issue_resolution = None
        
        # Convert to 0-10 scales where needed
        fill_rate_score = avg_fill_rate / 10
        order_accuracy_score = avg_order_accuracy / 10
        
        # Convert issue resolution time to a score (lower is better)
        if avg_issue_resolution is not None:
            # Assuming 72 hours as a reference point (3 days to resolve an issue)
            issue_resolution_score = max(0, 10 - (avg_issue_resolution / 7.2))
        else:
            issue_resolution_score = 5.0  # Default if no data
        
        # Weighted service score
        service_score = (
            avg_responsiveness * 0.3 +
            issue_resolution_score * 0.2 +
            fill_rate_score * 0.25 +
            order_accuracy_score * 0.25
        )
        
        return {
            'service_score': service_score,
            'responsiveness': avg_responsiveness,
            'issue_resolution_time': avg_issue_resolution,
            'fill_rate': avg_fill_rate,
            'order_accuracy': avg_order_accuracy
        }
    
    def calculate_combined_metrics(self, supplier_id, days=90):
        """
        Calculates all metrics for a supplier and returns a combined result
        
        Returns:
            dict: Dictionary containing all metrics
        """
        # Get active configuration for weights
        config = self.get_active_configuration()
        
        # Calculate individual metric categories
        quality_metrics = self.calculate_quality_metrics(supplier_id, days)
        delivery_metrics = self.calculate_delivery_metrics(supplier_id, days)
        price_metrics = self.calculate_price_metrics(supplier_id, days)
        service_metrics = self.calculate_service_metrics(supplier_id, days)
        
        # Get supplier info to access compliance score
        supplier_info = self.get_supplier_info(supplier_id)
        compliance_score = supplier_info.get('compliance_score', 5.0) if supplier_info else 5.0
        
        # Calculate overall score based on configuration weights
        # Include compliance score as part of the overall evaluation
        overall_score = (
            quality_metrics['quality_score'] * config.quality_weight +
            delivery_metrics['delivery_score'] * config.delivery_weight +
            price_metrics['price_score'] * config.price_weight +
            service_metrics['service_score'] * config.service_weight
        )
        
        # Adjust overall score with compliance score (giving it 20% weight)
        overall_score = overall_score * 0.8 + compliance_score * 0.2
        
        # Build combined metrics dictionary
        combined_metrics = {
            'supplier_id': supplier_id,
            'overall_score': overall_score,
            'quality_score': quality_metrics['quality_score'],
            'delivery_score': delivery_metrics['delivery_score'],
            'price_score': price_metrics['price_score'],
            'service_score': service_metrics['service_score'],
            'compliance_score': compliance_score,
            'quality_metrics': quality_metrics,
            'delivery_metrics': delivery_metrics,
            'price_metrics': price_metrics,
            'service_metrics': service_metrics,
            'calculation_date': date.today()
        }
        
        return combined_metrics
    
    def calculate_metrics_for_all_suppliers(self, days=90):
        """
        Calculates metrics for all active suppliers
        
        Returns:
            list: List of dictionaries with supplier metrics
        """
        # Get all active suppliers from User Service
        suppliers = self.user_service.get_active_suppliers()
        all_metrics = []
        
        for supplier in suppliers:
            metrics = self.calculate_combined_metrics(supplier['user']['id'], days)
            metrics['supplier_name'] = supplier['company_name']
            metrics['supplier_code'] = supplier['code']
            all_metrics.append(metrics)
        
        # Sort by overall score
        all_metrics.sort(key=lambda x: x['overall_score'], reverse=True)
        
        # Add rank
        for i, metrics in enumerate(all_metrics):
            metrics['rank'] = i + 1
        
        return all_metrics
        
    # New functions to satisfy the requirements of the environment.py file
    
    def get_quality_metrics(self, supplier_id, days=90):
        """
        Retrieves quality metrics for a supplier.
        This function is a wrapper around calculate_quality_metrics for use by the environment.
        
        Args:
            supplier_id (int): ID of the supplier
            days (int, optional): Number of days to look back. Defaults to 90.
            
        Returns:
            dict: Dictionary containing quality metrics
        """
        return self.calculate_quality_metrics(supplier_id, days)

    def get_delivery_metrics(self, supplier_id, days=90):
        """
        Retrieves delivery metrics for a supplier.
        This function is a wrapper around calculate_delivery_metrics for use by the environment.
        
        Args:
            supplier_id (int): ID of the supplier
            days (int, optional): Number of days to look back. Defaults to 90.
            
        Returns:
            dict: Dictionary containing delivery metrics
        """
        return self.calculate_delivery_metrics(supplier_id, days)

    def get_price_metrics(self, supplier_id, days=90):
        """
        Retrieves price metrics for a supplier.
        This function is a wrapper around calculate_price_metrics for use by the environment.
        
        Args:
            supplier_id (int): ID of the supplier
            days (int, optional): Number of days to look back. Defaults to 90.
            
        Returns:
            dict: Dictionary containing price metrics
        """
        return self.calculate_price_metrics(supplier_id, days)

    def get_service_metrics(self, supplier_id, days=90):
        """
        Retrieves service metrics for a supplier.
        This function is a wrapper around calculate_service_metrics for use by the environment.
        
        Args:
            supplier_id (int): ID of the supplier
            days (int, optional): Number of days to look back. Defaults to 90.
            
        Returns:
            dict: Dictionary containing service metrics
        """
        return self.calculate_service_metrics(supplier_id, days)
        
    def get_supplier_info(self, supplier_id):
        """
        Retrieves supplier information from the user service
        
        Args:
            supplier_id (int): ID of the supplier
            
        Returns:
            dict: Dictionary containing supplier information
        """
        try:
            # Get supplier information from the user service
            # Use get_supplier_by_id to match the function in UserServiceConnector
            supplier = self.user_service.get_supplier_by_id(supplier_id)
            
            if not supplier:
                return None
                
            # Extract relevant information
            supplier_info = {
                'id': supplier.get('user', {}).get('id'),
                'company_name': supplier.get('company_name', f"Supplier {supplier_id}"),
                'code': supplier.get('code', ''),
                'status': supplier.get('active', True),
                'compliance_score': supplier.get('compliance_score', 5.0),
                'registration_date': supplier.get('created_at')
            }
            
            return supplier_info
            
        except Exception as e:
            print(f"Error getting supplier info: {str(e)}")
            return None

    def get_supplier_metrics(self, supplier_id, days=90):
        """
        Gets all metrics for a supplier in a single call
        
        Args:
            supplier_id (int): The ID of the supplier
            days (int): Number of days to look back for metrics
            
        Returns:
            dict: Dictionary containing all supplier metrics
        """
        quality_metrics = self.get_quality_metrics(supplier_id, days)
        delivery_metrics = self.get_delivery_metrics(supplier_id, days)
        price_metrics = self.get_price_metrics(supplier_id, days)
        service_metrics = self.get_service_metrics(supplier_id, days)
        
        # Combine all metrics
        metrics = {
            'quality_score': quality_metrics.get('quality_score', 0),
            'delivery_score': delivery_metrics.get('delivery_score', 0),
            'price_score': price_metrics.get('price_score', 0),
            'service_score': service_metrics.get('service_score', 0),
            'overall_score': 0  # Will be calculated below
        }
        
        # Get weights from configuration
        config = self.get_active_configuration()
        weights = {
            'quality': config.quality_weight,
            'delivery': config.delivery_weight,
            'price': config.price_weight,
            'service': config.service_weight
        }
        
        # Calculate overall score using weighted average
        metrics['overall_score'] = (
            metrics['quality_score'] * weights['quality'] +
            metrics['delivery_score'] * weights['delivery'] +
            metrics['price_score'] * weights['price'] +
            metrics['service_score'] * weights['service']
        )
        
        return metrics