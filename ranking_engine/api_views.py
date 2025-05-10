"""
Supplier Ranking API

This module provides API endpoints for the Q-Learning based Supplier Ranking Service.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
import logging

from api.models import QLearningState, QLearningAction, QTableEntry
from ranking_engine.q_learning.agent import SupplierRankingAgent
from ranking_engine.q_learning.environment import SupplierEnvironment
from ranking_engine.q_learning.state_mapper import StateMapper
from ranking_engine.services.metrics_service import MetricsService
from ranking_engine.services.supplier_service import SupplierService
from connectors.warehouse_service_connector import WarehouseServiceConnector
from connectors.user_service_connector import UserServiceConnector

logger = logging.getLogger(__name__)


class FeedbackView(APIView):
    """
    Accept supplier performance feedback and update Q-values
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Extract data from request
        supplier_id = request.data.get('supplier_id')
        product_id = request.data.get('product_id')
        city = request.data.get('city')  # Using city instead of region
        delivery_time_days = request.data.get('delivery_time_days')
        quality_rating = request.data.get('quality_rating')
        order_accuracy = request.data.get('order_accuracy')
        issues = request.data.get('issues', 0)
        
        # Validate required fields
        if not all([supplier_id, product_id, quality_rating]):
            return Response(
                {"error": "supplier_id, product_id, and quality_rating are required fields"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get supplier details
        supplier_service = SupplierService()
        supplier = supplier_service.get_supplier(supplier_id)
        if not supplier:
            return Response(
                {"error": f"Supplier with ID {supplier_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create metrics from feedback
        metrics = {
            'quality_score': min(max(float(quality_rating) * 10, 1), 10),  # Convert to 1-10 scale
            'delivery_score': min(max(10 - min(float(delivery_time_days or 1), 10), 1), 10),  # Faster is better
            'price_score': 7.0,  # Use default or get from another service
            'service_score': min(max(10 - (float(issues) * 2), 1), 10),
            'overall_score': 0.0  # Will be calculated next
        }
        
        # Calculate overall score
        metrics['overall_score'] = (
            metrics['quality_score'] * 0.25 +
            metrics['delivery_score'] * 0.25 +
            metrics['price_score'] * 0.25 +
            metrics['service_score'] * 0.25
        )
        
        logger.info(f"Processing feedback for supplier {supplier_id} with metrics: {metrics}")
        
        # Use your existing StateMapper to get state
        state_mapper = StateMapper()
        state = state_mapper.get_state_from_metrics(metrics)
        
        # Use your environment to get reward
        environment = SupplierEnvironment()
        
        # Get actions for this state
        actions = environment.get_actions(state)
        
        # Use your agent to learn
        agent = SupplierRankingAgent()
        
        # Find current action and update based on feedback
        action = None
        for a in actions:
            if a.name.startswith("RANK_TIER_"):
                action = a
                break
        
        if not action:
            return Response(
                {"error": "No suitable action found for feedback"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate reward from metrics
        reward = environment.get_reward(supplier_id, state, action)
        
        # Get next state
        next_state = environment.next_state(supplier_id, action)
        
        # Update Q-value
        new_q_value = agent.learn(state, action, reward, next_state)
        
        # Get company name with fallback
        company_name = supplier.get('company_name', 
                      supplier.get('name',
                      supplier.get('user', {}).get('name', f"Unknown Supplier {supplier_id}")))
        
        return Response({
            "message": "Feedback received and Q-table updated",
            "q_value": new_q_value,
            "state": state.name,
            "action": action.name,
            "supplier": {
                "id": supplier_id,
                "company_name": company_name
            },
            "product_id": product_id,
            "city": city,
            "metrics": metrics
        })


class SupplierRankingView(APIView):
    """
    Get ranked suppliers for a product in a city
    """
    permission_classes = [AllowAny]

    def get(self, request):
        product_id = request.query_params.get('product_id')
        city = request.query_params.get('city')

        if not product_id:
            return Response(
                {"error": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            warehouse_service = WarehouseServiceConnector()
            suppliers = warehouse_service.get_suppliers_by_product(product_id)

            if not suppliers:
                return Response(
                    {"message": f"No suppliers found for product {product_id}"},
                    status=status.HTTP_200_OK
                )

            supplier_service = SupplierService()
            agent = SupplierRankingAgent()
            ranked_suppliers = []

            for supplier_id in suppliers:
                supplier = supplier_service.get_supplier(supplier_id)
                if not supplier:
                    continue

                # Filter by city if provided
                supplier_city = (
                    supplier.get("city")
                    or supplier.get("user", {}).get("city")
                )
                if city and supplier_city and supplier_city.lower() != city.lower():
                    continue

                # Perform Q-learning based ranking
                action, reward, ranking = agent.rank_supplier(
                    supplier_id,
                    update_ranking=True,
                    exploration=False
                )

                if not ranking:
                    continue

                # Fetch Q-value for the chosen state-action pair
                try:
                    q_entry = QTableEntry.objects.get(state=ranking.state, action=action)
                    q_value = q_entry.q_value
                except QTableEntry.DoesNotExist:
                    q_value = 0.0

                ranked_suppliers.append({
                    "supplier_id": ranking.supplier_id,
                    "company_name": ranking.supplier_name,
                    "score": ranking.overall_score,
                    "state": ranking.state.name,
                    "best_action": action.name,
                    "q_value": q_value,
                    "city": supplier_city
                })

            ranked_suppliers.sort(key=lambda x: x["score"], reverse=True)

            return Response({
                "product_id": product_id,
                "city": city,
                "suppliers": ranked_suppliers,
                "count": len(ranked_suppliers)
            })

        except Exception as e:
            logger.error(f"Error getting supplier rankings: {str(e)}")
            return Response(
                {"error": f"Failed to get supplier rankings: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class ManualTrainingView(APIView):
    """
    Manually trigger re-training (admin only)
    """
    permission_classes = [AllowAny]
    
    @transaction.atomic
    def post(self, request):
        try:
            # Create agent
            agent = SupplierRankingAgent()
            
            # Get training parameters
            iterations = int(request.data.get('iterations', 100))
            supplier_ids = request.data.get('supplier_ids', None)
            
            logger.info(f"Starting manual training with {iterations} iterations")
            
            # Perform batch training
            agent.batch_train(iterations=iterations, supplier_ids=supplier_ids)
            
            return Response({
                "message": "Q-table updated with historical data",
                "iterations": iterations,
                "supplier_count": len(supplier_ids) if supplier_ids else "all"
            })
        
        except Exception as e:
            logger.error(f"Error during manual training: {str(e)}")
            return Response(
                {"error": f"Training failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QValueView(APIView):
    """
    Debugging - retrieve Q-value for a given (state, action)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        supplier_id = request.query_params.get('supplier_id')
        
        if not supplier_id:
            return Response(
                {"error": "supplier_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Use metrics service to get metrics for this supplier
            metrics_service = MetricsService()
            metrics = metrics_service.calculate_combined_metrics(supplier_id)
            
            # Map to state
            state_mapper = StateMapper()
            state = state_mapper.get_state_from_metrics(metrics)
            
            # Get available actions
            environment = SupplierEnvironment()
            actions = environment.get_actions(state)
            
            # Get Q-values for each action
            q_values = []
            for action in actions:
                try:
                    q_entry = QTableEntry.objects.get(state=state, action=action)
                    q_values.append({
                        "action": action.name,
                        "q_value": q_entry.q_value,
                        "update_count": q_entry.update_count
                    })
                except QTableEntry.DoesNotExist:
                    q_values.append({
                        "action": action.name,
                        "q_value": 0.0,
                        "update_count": 0
                    })
            
            # Get supplier details
            supplier_service = SupplierService()
            supplier = supplier_service.get_supplier(supplier_id)
            
            # Get company name with fallback
            company_name = None
            if supplier:
                company_name = supplier.get('company_name', 
                              supplier.get('name',
                              supplier.get('user', {}).get('name', f"Unknown Supplier {supplier_id}")))
            
            return Response({
                "state": state.name,
                "supplier_id": supplier_id,
                "company_name": company_name,
                "q_values": q_values,
                "metrics": metrics
            })
            
        except Exception as e:
            logger.error(f"Error retrieving Q-values: {str(e)}")
            return Response(
                {"error": f"Failed to retrieve Q-values: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QTableView(APIView):
    """
    Export the Q-table (admin only)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Support filtering
            state_name = request.query_params.get('state')
            action_name = request.query_params.get('action')
            min_q_value = request.query_params.get('min_q_value')
            limit = int(request.query_params.get('limit', 100))
            
            # Start with all entries
            entries_query = QTableEntry.objects.all()
            
            # Apply filters if provided
            if state_name:
                entries_query = entries_query.filter(state__name__contains=state_name)
            
            if action_name:
                entries_query = entries_query.filter(action__name__contains=action_name)
            
            if min_q_value:
                entries_query = entries_query.filter(q_value__gte=float(min_q_value))
            
            # Limit the result count
            entries_query = entries_query.order_by('-q_value')[:limit]
            
            # Get the entries
            entries = entries_query.select_related('state', 'action')
            
            # Format for response
            q_table = []
            for entry in entries:
                q_table.append({
                    "state": entry.state.name,
                    "action": entry.action.name,
                    "q_value": entry.q_value,
                    "update_count": entry.update_count
                })
            
            return Response({
                "q_table_entries": q_table,
                "count": len(q_table),
                "total_entries": QTableEntry.objects.count()
            })
            
        except Exception as e:
            logger.error(f"Error retrieving Q-table: {str(e)}")
            return Response(
                {"error": f"Failed to retrieve Q-table: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 