"""
Supplier Service - Handles all supplier-related operations

This service acts as an abstraction layer for all supplier-related operations,
including data retrieval for the ranking system through external service connectors.
"""

from django.utils import timezone
from datetime import date, timedelta
import logging
from api.models import SupplierRanking
from connectors.user_service_connector import UserServiceConnector
from connectors.warehouse_service_connector import WarehouseServiceConnector
from connectors.order_service_connector import OrderServiceConnector

logger = logging.getLogger(__name__)

class SupplierService:
    """Service for managing supplier operations through external service connectors"""
    
    def __init__(self):
        """Initialize service with connectors to external services"""
        self.user_service = UserServiceConnector()
        self.warehouse_service = WarehouseServiceConnector()
        self.order_service = OrderServiceConnector()
    
    def get_active_suppliers(self):
        """
        Returns all active suppliers from User Service
        """
        try:
            return self.user_service.get_active_suppliers()
        except Exception as e:
            logger.error(f"Error retrieving active suppliers: {str(e)}")
            return []
    
    def get_active_supplier_ids(self):
        """
        Returns IDs of all active suppliers
        """
        try:
            suppliers = self.user_service.get_active_suppliers()
            return [supplier['user']['id'] for supplier in suppliers]
        except Exception as e:
            logger.error(f"Error retrieving active supplier IDs: {str(e)}")
            return []
    
    def get_active_supplier_count(self):
        """
        Returns count of active suppliers
        """
        try:
            return self.user_service.get_active_supplier_count()
        except Exception as e:
            logger.error(f"Error retrieving active supplier count: {str(e)}")
            return 0
    
    def get_supplier(self, supplier_id):
        """
        Returns a specific supplier by ID from User Service
        """
        try:
            return self.user_service.get_supplier_by_id(supplier_id)
        except Exception as e:
            logger.error(f"Error retrieving supplier {supplier_id}: {str(e)}")
            return None
    
    def get_supplier_info(self, supplier_id):
        """
        Returns detailed supplier information from User Service
        """
        try:
            supplier = self.user_service.get_supplier_by_id(supplier_id)
            if supplier:
                # Enhance with additional information if needed
                return supplier
            return None
        except Exception as e:
            logger.error(f"Error retrieving supplier info for {supplier_id}: {str(e)}")
            return None
    
    def get_supplier_products(self, supplier_id):
        """
        Returns all products offered by a supplier from Warehouse Service
        """
        try:
            return self.warehouse_service.get_supplier_products(supplier_id)
        except Exception as e:
            logger.error(f"Error retrieving products for supplier {supplier_id}: {str(e)}")
            return []
    
    def get_supplier_performance_history(self, supplier_id, days=90):
        """
        Returns performance history for a supplier for the given time period from Order Service
        """
        try:
            start_date = date.today() - timedelta(days=days)
            return self.order_service.get_supplier_performance(supplier_id, start_date=start_date)
        except Exception as e:
            logger.error(f"Error retrieving performance history for supplier {supplier_id}: {str(e)}")
            return []
    
    def get_supplier_transactions(self, supplier_id, days=90):
        """
        Returns transaction history for a supplier from Order Service
        """
        try:
            start_date = timezone.now() - timedelta(days=days)
            return self.order_service.get_supplier_transactions(supplier_id, start_date=start_date)
        except Exception as e:
            logger.error(f"Error retrieving transactions for supplier {supplier_id}: {str(e)}")
            return []
    
    def get_supplier_ranking_history(self, supplier_id, days=90):
        """
        Returns ranking history for a supplier from our local database
        """
        start_date = date.today() - timedelta(days=days)
        return SupplierRanking.objects.filter(
            supplier_id=supplier_id,
            date__gte=start_date
        ).order_by('date')
    
    def get_latest_supplier_rankings(self):
        """
        Returns the most recent ranking for each supplier from our local database
        """
        from django.db.models import Max
        
        latest_date = SupplierRanking.objects.aggregate(Max('date'))['date__max']
        if not latest_date:
            return []
            
        return SupplierRanking.objects.filter(date=latest_date).order_by('rank')
    
    def get_top_ranked_suppliers(self, count=10, category=None):
        """
        Returns the top ranked suppliers, optionally filtered by product category
        """
        from django.db.models import Max
        
        # Get latest rankings
        latest_date = SupplierRanking.objects.aggregate(Max('date'))['date__max']
        if not latest_date:
            return []
            
        rankings = SupplierRanking.objects.filter(date=latest_date).order_by('rank')
        
        if category:
            # Get suppliers who offer products in the specified category
            try:
                supplier_ids = self.warehouse_service.get_suppliers_by_category(category)
                rankings = rankings.filter(supplier_id__in=supplier_ids)
            except Exception as e:
                logger.error(f"Error filtering suppliers by category {category}: {str(e)}")
        
        return rankings[:count]
    
    def get_supplier_category_performance(self, supplier_id):
        """
        Returns supplier performance grouped by product category from Order Service
        """
        try:
            return self.order_service.get_supplier_category_performance(supplier_id)
        except Exception as e:
            logger.error(f"Error retrieving category performance for supplier {supplier_id}: {str(e)}")
            return {}
    
    def get_all_suppliers(self):
        """
        Returns all suppliers from User Service
        
        Returns:
            list: List of supplier dictionaries
        """
        try:
            return self.user_service.get_all_suppliers()
        except Exception as e:
            logger.error(f"Error retrieving all suppliers: {str(e)}")
            return []
    
    # def update_supplier_preferences(self, supplier_id, preferences_data):
    #     """
    #     Updates preference flags for a supplier's products through Warehouse Service
    #     """
    #     try:
    #         success = self.warehouse_service.update_supplier_preferences(supplier_id, preferences_data)
    #         return success
    #     except Exception as e:
    #         logger.error(f"Error updating preferences for supplier {supplier_id}: {str(e)}")
    #         return False