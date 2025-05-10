from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Q, F, Sum, Max
from django.http import HttpResponse
from rest_framework import viewsets, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import csv
import io
import requests

from .models import (
    QLearningState,
    QLearningAction,
    QTableEntry,
    SupplierRanking,
    SupplierPerformanceCache,
    RankingConfiguration,
    RankingEvent
)

from .serializers import (
    QLearningStateSerializer,
    QLearningActionSerializer,
    QTableEntrySerializer,
    SupplierRankingSerializer,
    SupplierPerformanceCacheSerializer,
    RankingConfigurationSerializer,
    RankingEventSerializer,
    TrainQLearningModelSerializer,
    SupplierRankingInputSerializer,
    SupplierMetricsSerializer,
    SupplierRecommendationSerializer
)

# Configuration for service endpoints
SERVICE_ENDPOINTS = {
    'user_service': 'http://user-service-api/api/v1',
    'warehouse_service': 'http://warehouse-service-api/api/v1',
    'order_service': 'http://order-service-api/api/v1',
}

# Helper function to get data from another service
def get_service_data(service_name, endpoint, params=None):
    """
    Helper function to fetch data from other services.
    """
    if service_name not in SERVICE_ENDPOINTS:
        raise ValueError(f"Unknown service: {service_name}")
    
    url = f"{SERVICE_ENDPOINTS[service_name]}/{endpoint}"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Log the error
        print(f"Error fetching data from {service_name}: {str(e)}")
        raise

# Q-Learning related ViewSets
class QLearningStateViewSet(viewsets.ModelViewSet):
    queryset = QLearningState.objects.all()
    serializer_class = QLearningStateSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class QLearningActionViewSet(viewsets.ModelViewSet):
    queryset = QLearningAction.objects.all()
    serializer_class = QLearningActionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class QTableEntryViewSet(viewsets.ModelViewSet):
    queryset = QTableEntry.objects.all()
    serializer_class = QTableEntrySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'action']
    ordering_fields = ['q_value', 'update_count', 'last_updated']


class SupplierRankingViewSet(viewsets.ModelViewSet):
    queryset = SupplierRanking.objects.all()
    serializer_class = SupplierRankingSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['supplier_id', 'date', 'rank']
    ordering_fields = ['date', 'rank', 'overall_score']


class SupplierPerformanceCacheViewSet(viewsets.ModelViewSet):
    queryset = SupplierPerformanceCache.objects.all()
    serializer_class = SupplierPerformanceCacheSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['supplier_id', 'date']
    ordering_fields = ['date', 'quality_score', 'on_time_delivery_rate', 'price_competitiveness']


class RankingConfigurationViewSet(viewsets.ModelViewSet):
    queryset = RankingConfiguration.objects.all()
    serializer_class = RankingConfigurationSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    ordering_fields = ['created_at']
    
    @action(detail=False, methods=['get'])
    def active_config(self, request):
        active_config = RankingConfiguration.objects.filter(is_active=True).first()
        if active_config:
            serializer = self.get_serializer(active_config)
            return Response(serializer.data)
        return Response({"detail": "No active configuration found"}, status=status.HTTP_404_NOT_FOUND)


class RankingEventViewSet(viewsets.ModelViewSet):
    queryset = RankingEvent.objects.all()
    serializer_class = RankingEventSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['event_type', 'supplier_id']
    ordering_fields = ['timestamp']


# Q-Learning and Training Views
class TrainQLearningModelView(APIView):
    """
    API endpoint to train the Q-Learning model for supplier ranking.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = TrainQLearningModelSerializer(data=request.data)
        if serializer.is_valid():
            # Log the training event
            RankingEvent.objects.create(
                event_type='RANKING_STARTED',
                description='Training Q-Learning model',
                metadata=serializer.validated_data
            )
            
            # Here we would implement the actual training logic
            # For now, we'll just return a mock response
            return Response({
                "message": "Q-Learning model training started",
                "params": serializer.validated_data,
                "status": "TRAINING_STARTED",
                "estimated_completion_time": "10 minutes"
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PredictSupplierRankingView(APIView):
    """
    API endpoint to predict supplier rankings using the trained Q-Learning model.
    """
    def post(self, request):
        supplier_id = request.data.get('supplier_id')
        if not supplier_id:
            return Response({"error": "supplier_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify supplier exists in user service
        try:
            supplier_data = get_service_data('user_service', f'suppliers/{supplier_id}')
        except Exception as e:
            return Response({"error": f"Failed to fetch supplier data: {str(e)}"}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not supplier_data:
            return Response({"error": "Supplier not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get the latest performance cache for this supplier
        latest_performance = SupplierPerformanceCache.objects.filter(supplier_id=supplier_id).order_by('-date').first()
        if not latest_performance:
            return Response({"error": "No performance data available for this supplier"}, 
                           status=status.HTTP_404_NOT_FOUND)
            
        # In a real implementation, we would:
        # 1. Load the latest Q-table
        # 2. Map the supplier's current metrics to a state
        # 3. Find the optimal action using the Q-table
        # 4. Calculate the predicted ranking

        # For now, we'll just return a mock response
        return Response({
            "supplier_id": supplier_id,
            "supplier_name": supplier_data.get('name', 'Unknown Supplier'),
            "predicted_rank": 3,
            "predicted_score": 8.7,
            "confidence": 0.85,
            "recommendation": "This supplier is predicted to maintain high performance.",
            "potential_improvements": [
                "Reducing lead time could improve delivery score",
                "Addressing quality issues could raise overall ranking"
            ]
        })


# Analytics Views
class SupplierMetricsView(APIView):
    """
    API endpoint to retrieve comprehensive metrics for a specific supplier.
    """
    def get(self, request, supplier_id):
        # Verify supplier exists in user service
        try:
            supplier_data = get_service_data('user_service', f'suppliers/{supplier_id}')
        except Exception as e:
            return Response({"error": f"Failed to fetch supplier data: {str(e)}"}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not supplier_data:
            return Response({"error": "Supplier not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get date range filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Build the query filters
        filters = Q(supplier_id=supplier_id)
        if start_date:
            filters &= Q(date__gte=start_date)
        if end_date:
            filters &= Q(date__lte=end_date)
        
        # Get performance metrics from cache
        performances = SupplierPerformanceCache.objects.filter(filters)
        
        # If no performances found for the date range
        if not performances.exists():
            return Response({
                "supplier_id": supplier_id,
                "supplier_name": supplier_data.get('name', 'Unknown Supplier'),
                "error": "No performance data found for the specified date range"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate averages
        avg_metrics = performances.aggregate(
            avg_quality_score=Avg('quality_score'),
            avg_defect_rate=Avg('defect_rate'),
            avg_return_rate=Avg('return_rate'),
            avg_on_time_delivery_rate=Avg('on_time_delivery_rate'),
            avg_delay_days=Avg('average_delay_days'),
            avg_price_competitiveness=Avg('price_competitiveness'),
            avg_responsiveness=Avg('responsiveness'),
            avg_fill_rate=Avg('fill_rate'),
            avg_order_accuracy=Avg('order_accuracy'),
        )
        
        # Get latest ranking
        latest_ranking = SupplierRanking.objects.filter(supplier_id=supplier_id).order_by('-date').first()
        rank_trend = list(SupplierRanking.objects.filter(supplier_id=supplier_id).order_by('date').values_list('rank', flat=True))
        
        # Combine all data
        response_data = {
            "supplier_id": supplier_id,
            "supplier_name": supplier_data.get('name', 'Unknown Supplier'),
            "metrics_period": {
                "start_date": start_date or performances.earliest('date').date,
                "end_date": end_date or performances.latest('date').date,
                "data_points": performances.count()
            },
            "quality_metrics": {
                "avg_quality_score": avg_metrics['avg_quality_score'],
                "avg_defect_rate": avg_metrics['avg_defect_rate'],
                "avg_return_rate": avg_metrics['avg_return_rate']
            },
            "delivery_metrics": {
                "avg_on_time_delivery_rate": avg_metrics['avg_on_time_delivery_rate'],
                "avg_delay_days": avg_metrics['avg_delay_days']
            },
            "price_metrics": {
                "avg_price_competitiveness": avg_metrics['avg_price_competitiveness']
            },
            "service_metrics": {
                "avg_responsiveness": avg_metrics['avg_responsiveness'],
                "avg_fill_rate": avg_metrics['avg_fill_rate'],
                "avg_order_accuracy": avg_metrics['avg_order_accuracy']
            },
            "ranking_data": {
                "current_rank": latest_ranking.rank if latest_ranking else None,
                "current_overall_score": latest_ranking.overall_score if latest_ranking else None,
                "rank_trend": rank_trend
            }
        }
        
        return Response(response_data)


class SupplierRankingHistoryView(APIView):
    """
    API endpoint to retrieve historical ranking data for all suppliers.
    """
    def get(self, request):
        # Get date range filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Build the query filters
        filters = Q()
        if start_date:
            filters &= Q(date__gte=start_date)
        if end_date:
            filters &= Q(date__lte=end_date)
        
        # Get all unique dates in the specified range
        ranking_dates = SupplierRanking.objects.filter(filters).values_list('date', flat=True).distinct().order_by('date')
        
        # If no rankings found for the date range
        if not ranking_dates:
            return Response({
                "error": "No ranking data found for the specified date range"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Prepare the response data
        ranking_history = []
        
        for date in ranking_dates:
            # Get all rankings for this date
            rankings = SupplierRanking.objects.filter(date=date).order_by('rank')
            
            # For each ranking, get the supplier name from cache or service
            date_rankings = []
            for rank in rankings:
                # Try to get supplier name from cache
                supplier_name = rank.supplier_name
                
                # If not available, try to get from user service
                if not supplier_name:
                    try:
                        supplier_data = get_service_data('user_service', f'suppliers/{rank.supplier_id}')
                        supplier_name = supplier_data.get('name', 'Unknown Supplier')
                    except Exception:
                        supplier_name = f"Supplier {rank.supplier_id}"
                
                date_rankings.append({
                    "supplier_id": rank.supplier_id,
                    "supplier_name": supplier_name,
                    "rank": rank.rank,
                    "overall_score": rank.overall_score,
                    "quality_score": rank.quality_score,
                    "delivery_score": rank.delivery_score,
                    "price_score": rank.price_score,
                    "service_score": rank.service_score
                })
            
            # Add to history
            ranking_history.append({
                "date": date,
                "rankings": date_rankings
            })
        
        return Response({
            "start_date": start_date or ranking_dates[0],
            "end_date": end_date or ranking_dates[len(ranking_dates)-1],
            "number_of_dates": len(ranking_dates),
            "ranking_history": ranking_history
        })


class PerformanceDashboardView(APIView):
    """
    API endpoint to get aggregate supplier performance metrics
    for creating dashboards and reports.
    """
    def get(self, request):
        # Get data for the last 90 days by default
        days = int(request.query_params.get('days', 90))
        
        # Get all supplier rankings
        latest_date = SupplierRanking.objects.aggregate(Max('date'))['date__max']
        
        if not latest_date:
            return Response({"error": "No ranking data available"}, status=status.HTTP_404_NOT_FOUND)
            
        latest_rankings = SupplierRanking.objects.filter(date=latest_date).order_by('rank')
        
        # Aggregate performance metrics
        avg_quality = latest_rankings.aggregate(Avg('quality_score'))['quality_score__avg'] or 0
        avg_delivery = latest_rankings.aggregate(Avg('delivery_score'))['delivery_score__avg'] or 0
        avg_price = latest_rankings.aggregate(Avg('price_score'))['price_score__avg'] or 0
        avg_service = latest_rankings.aggregate(Avg('service_score'))['service_score__avg'] or 0
        avg_overall = latest_rankings.aggregate(Avg('overall_score'))['overall_score__avg'] or 0
        
        # Get performance metrics from cache
        latest_cache_date = SupplierPerformanceCache.objects.aggregate(Max('date'))['date__max']
        if latest_cache_date:
            latest_cache = SupplierPerformanceCache.objects.filter(date=latest_cache_date)
            avg_defect_rate = latest_cache.aggregate(Avg('defect_rate'))['defect_rate__avg'] or 0
            avg_return_rate = latest_cache.aggregate(Avg('return_rate'))['return_rate__avg'] or 0
            avg_on_time_rate = latest_cache.aggregate(Avg('on_time_delivery_rate'))['on_time_delivery_rate__avg'] or 0
            avg_compliance = latest_cache.aggregate(Avg('compliance_score'))['compliance_score__avg'] or 0
        else:
            avg_defect_rate = 0
            avg_return_rate = 0
            avg_on_time_rate = 0
            avg_compliance = 0
            
        # Get top and bottom 5 suppliers
        top_suppliers = [
            {
                "supplier_id": r.supplier_id,
                "supplier_name": r.supplier_name,
                "rank": r.rank,
                "overall_score": r.overall_score,
                "quality_score": r.quality_score,
                "delivery_score": r.delivery_score,
                "price_score": r.price_score,
                "service_score": r.service_score,
                "compliance_score": SupplierPerformanceCache.objects.filter(
                    supplier_id=r.supplier_id, date=latest_cache_date
                ).first().compliance_score if latest_cache_date else None
            }
            for r in latest_rankings[:5]
        ]
        
        bottom_suppliers = [
            {
                "supplier_id": r.supplier_id,
                "supplier_name": r.supplier_name,
                "rank": r.rank,
                "overall_score": r.overall_score,
                "quality_score": r.quality_score,
                "delivery_score": r.delivery_score,
                "price_score": r.price_score,
                "service_score": r.service_score,
                "compliance_score": SupplierPerformanceCache.objects.filter(
                    supplier_id=r.supplier_id, date=latest_cache_date
                ).first().compliance_score if latest_cache_date else None
            }
            for r in latest_rankings.reverse()[:5]
        ]
        
        # Get metrics over time (for charts)
        # Group by date and calculate average scores
        time_series_data = SupplierRanking.objects.values('date').annotate(
            avg_overall=Avg('overall_score'),
            avg_quality=Avg('quality_score'),
            avg_delivery=Avg('delivery_score'),
            avg_price=Avg('price_score'),
            avg_service=Avg('service_score')
        ).order_by('date')
        
        time_series = [
            {
                "date": entry['date'],
                "avg_overall": entry['avg_overall'],
                "avg_quality": entry['avg_quality'],
                "avg_delivery": entry['avg_delivery'],
                "avg_price": entry['avg_price'],
                "avg_service": entry['avg_service']
            }
            for entry in time_series_data
        ]
        
        # Build response
        response_data = {
            "average_scores": {
                "overall": round(avg_overall, 2),
                "quality": round(avg_quality, 2),
                "delivery": round(avg_delivery, 2),
                "price": round(avg_price, 2),
                "service": round(avg_service, 2),
                "compliance": round(avg_compliance, 2)
            },
            "key_metrics": {
                "defect_rate": round(avg_defect_rate, 2),
                "return_rate": round(avg_return_rate, 2),
                "on_time_delivery_rate": round(avg_on_time_rate, 2)
            },
            "top_suppliers": top_suppliers,
            "bottom_suppliers": bottom_suppliers,
            "time_series": time_series,
            "supplier_count": latest_rankings.count(),
            "data_as_of": latest_date
        }
        
        return Response(response_data)


# Recommendation Views
class SupplierRecommendationView(APIView):
    """
    API endpoint to get supplier recommendations based on product requirements.
    """
    def post(self, request):
        serializer = SupplierRecommendationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract requirements
        product_id = serializer.validated_data.get('product_id')
        quantity = serializer.validated_data.get('quantity', 1)
        delivery_date = serializer.validated_data.get('delivery_date')
        prioritize_quality = serializer.validated_data.get('prioritize_quality', False)
        prioritize_delivery = serializer.validated_data.get('prioritize_delivery', False)
        
        # Get suppliers that can provide this product
        try:
            suppliers_providing_product = get_service_data(
                'warehouse_service', 
                f'products/{product_id}/suppliers'
            )
        except Exception as e:
            return Response({"error": f"Error fetching suppliers: {str(e)}"}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not suppliers_providing_product:
            return Response({"message": "No suppliers found for this product"}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        # For each supplier, get their performance data
        recommendations = []
        for sp in suppliers_providing_product:
            supplier_id = sp.get('supplier_id')
            
            # Get latest performance cache
            latest_performance = SupplierPerformanceCache.objects.filter(
                supplier_id=supplier_id
            ).order_by('-date').first()
            
            if latest_performance:
                # Get latest ranking
                latest_ranking = SupplierRanking.objects.filter(supplier_id=supplier_id).order_by('-date').first()
                
                # Get supplier data to access compliance score
                try:
                    connector = UserServiceConnector()
                    supplier_data = connector.get_supplier_by_id(supplier_id)
                    compliance_score = supplier_data.get('compliance_score', 5.0) if supplier_data else 5.0
                except Exception:
                    compliance_score = 5.0
                
                # Calculate a recommendation score based on the requirements
                recommendation_score = 0
                
                # Base score is the overall supplier ranking score
                if latest_ranking:
                    recommendation_score = latest_ranking.overall_score
                else:
                    # If no ranking exists, use a weighted combination of performance metrics and compliance score
                    recommendation_score = (
                        latest_performance.quality_score * 0.25 +
                        latest_performance.on_time_delivery_rate / 10 * 0.25 +  # Convert to 0-10 scale
                        latest_performance.price_competitiveness * 0.25 +
                        latest_performance.responsiveness * 0.05 +
                        compliance_score * 0.2
                    )
                
                # Check if supplier can deliver by the requested date
                lead_time_days = sp.get('lead_time_days', 0)
                if delivery_date:
                    from datetime import datetime, timedelta
                    today = datetime.now().date()
                    delivery_date_obj = datetime.strptime(delivery_date, '%Y-%m-%d').date() if isinstance(delivery_date, str) else delivery_date
                    days_until_delivery = (delivery_date_obj - today).days
                    can_deliver_on_time = days_until_delivery >= lead_time_days
                else:
                    can_deliver_on_time = True
                
                # Adjust score based on priorities
                if prioritize_quality:
                    recommendation_score += latest_performance.quality_score * 0.5
                
                if prioritize_delivery:
                    if can_deliver_on_time:
                        recommendation_score += 3
                    else:
                        recommendation_score -= 5
                    
                    recommendation_score += latest_performance.on_time_delivery_rate / 10
                
                # Adjust for price (lower is better)
                unit_price = sp.get('unit_price', 0)
                recommendation_score -= (unit_price / 100)  # Adjust weight as needed
                
                # Include compliance score in recommendation
                recommendation_score += compliance_score * 0.3
                
                # Store recommendation
                recommendations.append({
                    "supplier_id": supplier_id,
                    "supplier_name": sp.get('supplier_name', f"Supplier {supplier_id}"),
                    "unit_price": float(unit_price),
                    "lead_time_days": sp.get('lead_time_days', 0),
                    "can_deliver_on_time": can_deliver_on_time,
                    "quality_score": latest_performance.quality_score,
                    "on_time_delivery_rate": latest_performance.on_time_delivery_rate,
                    "compliance_score": compliance_score,
                    "recommendation_score": round(recommendation_score, 2),
                    "is_preferred": sp.get('is_preferred', False)
                })
        
        # Sort by recommendation score (higher is better)
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return Response({
            "product_id": product_id,
            "quantity": quantity,
            "delivery_date": delivery_date,
            "recommendations": recommendations
        })


class OptimalOrderAllocationView(APIView):
    """
    API endpoint to determine optimal order allocation across multiple suppliers.
    """
    def post(self, request):
        product_id = request.data.get('product_id')
        total_quantity = request.data.get('total_quantity')
        delivery_date = request.data.get('delivery_date')
        
        if not all([product_id, total_quantity, delivery_date]):
            return Response({
                "error": "product_id, total_quantity, and delivery_date are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get product data from warehouse service
        try:
            product_data = get_service_data('warehouse_service', f'products/{product_id}')
        except Exception as e:
            return Response({"error": f"Failed to fetch product data: {str(e)}"}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not product_data:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Get suppliers for this product from warehouse service
        try:
            supplier_products = get_service_data('warehouse_service', 'supplier-products', 
                                              {'product_id': product_id})
        except Exception as e:
            return Response({"error": f"Failed to fetch supplier-product data: {str(e)}"}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not supplier_products:
            return Response({
                "message": "No suppliers found for the specified product"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Sort suppliers by unit price (cheapest first)
        sorted_suppliers = sorted(supplier_products, key=lambda sp: sp.get('unit_price', float('inf')))
        
        # Allocate orders to suppliers
        allocations = []
        remaining_quantity = total_quantity
        
        for sp in sorted_suppliers:
            if remaining_quantity <= 0:
                break
            
            # Get constraints for this supplier
            supplier_id = sp['supplier_id']
            min_order_quantity = sp.get('minimum_order_quantity', 1)
            max_order_quantity = sp.get('maximum_order_quantity')
            
            # Determine how much to allocate to this supplier
            allocation_quantity = min(remaining_quantity, max_order_quantity if max_order_quantity else remaining_quantity)
            
            # Ensure minimum order quantity
            if allocation_quantity < min_order_quantity:
                continue
            
            # Get supplier name (either from cache or service)
            supplier_name = sp.get('supplier_name')
            if not supplier_name:
                try:
                    supplier_data = get_service_data('user_service', f'suppliers/{supplier_id}')
                    supplier_name = supplier_data.get('name', f"Supplier {supplier_id}")
                except Exception:
                    supplier_name = f"Supplier {supplier_id}"
            
            allocations.append({
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "allocation_quantity": allocation_quantity,
                "unit_price": float(sp.get('unit_price', 0)),
                "total_cost": float(sp.get('unit_price', 0) * allocation_quantity),
                "lead_time_days": sp.get('lead_time_days', 0)
            })
            
            remaining_quantity -= allocation_quantity
        
        if remaining_quantity > 0:
            return Response({
                "message": "Could not allocate the entire order quantity",
                "product_id": product_id,
                "product_name": product_data.get('name', f"Product {product_id}"),
                "total_quantity": total_quantity,
                "allocated_quantity": total_quantity - remaining_quantity,
                "unallocated_quantity": remaining_quantity,
                "allocations": allocations
            }, status=status.HTTP_206_PARTIAL_CONTENT)
        
        # Calculate total cost
        total_cost = sum(a['total_cost'] for a in allocations)
        
        return Response({
            "product_id": product_id,
            "product_name": product_data.get('name', f"Product {product_id}"),
            "total_quantity": total_quantity,
            "delivery_date": delivery_date,
            "total_cost": total_cost,
            "allocations": allocations
        })


# Integration Views
class DemandForecastIntegrationView(APIView):
    """
    API endpoint to integrate with Group 29's Demand Forecasting system.
    """
    def post(self, request):
        # This would be implemented according to the API contract with Group 29
        # For now, we'll just return a mock response
        return Response({
            "message": "Successfully integrated with Demand Forecasting system",
            "forecast_data": {
                "product_id": request.data.get('product_id', 1),
                "forecasted_demand": [
                    {"date": "2025-06-01", "quantity": 150},
                    {"date": "2025-07-01", "quantity": 175},
                    {"date": "2025-08-01", "quantity": 200}
                ]
            }
        })


class BlockchainDataIntegrationView(APIView):
    """
    API endpoint to integrate with Group 30's Blockchain system.
    """
    def post(self, request):
        # This would be implemented according to the API contract with Group 30
        # For now, we'll just return a mock response
        
        blockchain_reference = request.data.get('blockchain_reference')
        
        if not blockchain_reference:
            return Response({
                "error": "blockchain_reference is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            "message": "Successfully retrieved data from Blockchain system",
            "blockchain_data": {
                "reference": blockchain_reference,
                "transaction_hash": "0x1234567890abcdef",
                "timestamp": "2025-05-01T12:34:56Z",
                "status": "CONFIRMED",
                "supplier_id": request.data.get('supplier_id', 1),
                "product_id": request.data.get('product_id', 1),
                "quantity": request.data.get('quantity', 100),
                "verified": True
            }
        })


class LogisticsIntegrationView(APIView):
    """
    API endpoint to integrate with Group 32's Logistics system.
    """
    def post(self, request):
        # This would be implemented according to the API contract with Group 32
        # For now, we'll just return a mock response
        
        supplier_id = request.data.get('supplier_id')
        destination = request.data.get('destination')
        
        if not all([supplier_id, destination]):
            return Response({
                "error": "supplier_id and destination are required"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # We don't have direct access to Supplier model anymore
        # Instead, we would make an API call to the User Service to get supplier info
        # For now, we'll just assume the API call succeeded
        
        return Response({
            "message": "Successfully retrieved logistics data",
            "logistics_data": {
                "supplier_id": supplier_id,
                "supplier_location": "Retrieved from User Service API",  # This would come from the User Service
                "destination": destination,
                "estimated_transit_time": 5,  # days
                "route_efficiency_score": 8.5,
                "carbon_footprint": 2.3,  # tons of CO2
                "recommended_carrier": "Eco Logistics Inc."
            }
        })


# System Management Views
class ResetQTableView(APIView):
    """
    API endpoint to reset the Q-table for training from scratch.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Delete all existing Q-table entries
        QTableEntry.objects.all().delete()
        
        # Initialize with default values if specified
        initialize = request.data.get('initialize', False)
        
        if initialize:
            # Get all states and actions
            states = QLearningState.objects.all()
            actions = QLearningAction.objects.all()
            
            # Create empty Q-table entries
            entries_created = 0
            for state in states:
                for action in actions:
                    QTableEntry.objects.create(
                        state=state,
                        action=action,
                        q_value=0.0
                    )
                    entries_created += 1
            
            return Response({
                "message": "Q-table has been reset and initialized",
                "entries_created": entries_created
            })
        else:
            return Response({
                "message": "Q-table has been reset"
            })


class ExportRankingDataView(APIView):
    """
    API endpoint to export supplier ranking data.
    """
    def get(self, request):
        # Get export format
        export_format = request.query_params.get('format', 'json')
        
        # Get date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Build the query filters
        filters = Q()
        if start_date:
            filters &= Q(date__gte=start_date)
        if end_date:
            filters &= Q(date__lte=end_date)
        
        # Get all rankings
        rankings = SupplierRanking.objects.filter(filters).order_by('date', 'rank')
        
        if not rankings.exists():
            return Response({"error": "No ranking data found for the specified date range"}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        if export_format.lower() == 'csv':
            # Create a CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="supplier_rankings.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Date', 'Supplier ID', 'Supplier Name', 'Rank', 'Overall Score',
                'Quality Score', 'Delivery Score', 'Price Score', 'Service Score'
            ])
            
            for ranking in rankings:
                writer.writerow([
                    ranking.date,
                    ranking.supplier_id,
                    ranking.supplier_name,
                    ranking.rank,
                    ranking.overall_score,
                    ranking.quality_score,
                    ranking.delivery_score,
                    ranking.price_score,
                    ranking.service_score
                ])
            
            return response
        else:  # Default to JSON
            # Process data for JSON export
            ranking_data = []
            for ranking in rankings:
                ranking_data.append({
                    "date": ranking.date,
                    "supplier_id": ranking.supplier_id,
                    "supplier_name": ranking.supplier_name,
                    "rank": ranking.rank,
                    "overall_score": ranking.overall_score,
                    "quality_score": ranking.quality_score,
                    "delivery_score": ranking.delivery_score,
                    "price_score": ranking.price_score,
                    "service_score": ranking.service_score
                })
            
            return Response({
                "export_date": datetime.now().date(),
                "date_range": {
                    "start_date": start_date or rankings.first().date,
                    "end_date": end_date or rankings.last().date
                },
                "rankings": ranking_data
            })


class ImportPerformanceDataView(APIView):
    """
    API endpoint to import supplier performance cache data.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if 'file' not in request.FILES:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        
        # Check file type
        if file.name.endswith('.csv'):
            # Process CSV file
            content = file.read().decode('utf-8')
            csv_reader = csv.reader(io.StringIO(content))
            
            # Read header row
            header = next(csv_reader, None)
            if not header:
                return Response({"error": "Empty file"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Define required columns
            required_columns = [
                'supplier_id', 'supplier_name', 'date', 'quality_score', 'defect_rate', 
                'on_time_delivery_rate', 'price_competitiveness'
            ]
            
            # Validate header
            missing_columns = [col for col in required_columns if col not in header]
            if missing_columns:
                return Response({
                    "error": f"Missing required columns: {', '.join(missing_columns)}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Map column indices
            column_indices = {column: header.index(column) for column in header}
            
            # Process data rows
            records_processed = 0
            records_skipped = 0
            records_created = 0
            records_updated = 0
            error_records = []
            
            for row_idx, row in enumerate(csv_reader, start=2):  # Start from 2 for human-readable row numbers
                if len(row) != len(header):
                    records_skipped += 1
                    error_records.append({
                        "row": row_idx,
                        "error": "Column count mismatch"
                    })
                    continue
                
                try:
                    # Extract data
                    supplier_id = int(row[column_indices['supplier_id']])
                    supplier_name = row[column_indices['supplier_name']]
                    date_str = row[column_indices['date']]
                    
                    try:
                        date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        records_skipped += 1
                        error_records.append({
                            "row": row_idx,
                            "error": f"Invalid date format: '{date_str}', expected YYYY-MM-DD"
                        })
                        continue
                    
                    # Extract performance metrics
                    performance_data = {
                        'supplier_id': supplier_id,
                        'supplier_name': supplier_name,
                        'date': date
                    }
                    
                    # Add numeric fields with validation
                    numeric_fields = [
                        'quality_score', 'defect_rate', 'return_rate', 
                        'on_time_delivery_rate', 'average_delay_days', 
                        'price_competitiveness', 'responsiveness', 
                        'fill_rate', 'order_accuracy', 'compliance_score',
                        'demand_forecast_accuracy', 'logistics_efficiency'
                    ]
                    
                    for field in numeric_fields:
                        if field in column_indices and row[column_indices[field]]:
                            try:
                                performance_data[field] = float(row[column_indices[field]])
                            except ValueError:
                                records_skipped += 1
                                error_records.append({
                                    "row": row_idx,
                                    "error": f"Invalid numeric value for {field}: '{row[column_indices[field]]}'"
                                })
                                continue
                    
                    # Create or update record
                    performance, created = SupplierPerformanceCache.objects.update_or_create(
                        supplier_id=supplier_id,
                        date=date,
                        defaults=performance_data
                    )
                    
                    records_processed += 1
                    if created:
                        records_created += 1
                    else:
                        records_updated += 1
                        
                except Exception as e:
                    records_skipped += 1
                    error_records.append({
                        "row": row_idx,
                        "error": str(e)
                    })
            
            return Response({
                "message": "Import completed",
                "records_processed": records_processed,
                "records_created": records_created,
                "records_updated": records_updated,
                "records_skipped": records_skipped,
                "errors": error_records[:10],  # Limit number of errors returned
                "total_errors": len(error_records)
            })
        
        elif file.name.endswith(('.xlsx', '.xls')):
            return Response({
                "error": "Excel file format not supported yet. Please upload CSV file."
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                "error": "Unsupported file format. Please upload CSV file."
            }, status=status.HTTP_400_BAD_REQUEST)


class APIDocumentationView(APIView):
    """
    API endpoint to provide documentation for all available endpoints.
    """
    def get(self, request):
        base_url = request.build_absolute_uri('/').rstrip('/')
        
        # Build documentation for all endpoints
        endpoints = [
            # Basic CRUD endpoints for models in our service
            {
                "name": "Q-Learning States",
                "description": "CRUD operations for Q-Learning states",
                "endpoints": [
                    {"method": "GET", "url": f"{base_url}/q-learning-states/", "description": "List all states"},
                    {"method": "POST", "url": f"{base_url}/q-learning-states/", "description": "Create a new state"},
                    {"method": "GET", "url": f"{base_url}/q-learning-states/{{id}}/", "description": "Retrieve a state"},
                    {"method": "PUT", "url": f"{base_url}/q-learning-states/{{id}}/", "description": "Update a state"},
                    {"method": "DELETE", "url": f"{base_url}/q-learning-states/{{id}}/", "description": "Delete a state"}
                ]
            },
            {
                "name": "Q-Learning Actions",
                "description": "CRUD operations for Q-Learning actions",
                "endpoints": [
                    {"method": "GET", "url": f"{base_url}/q-learning-actions/", "description": "List all actions"},
                    {"method": "POST", "url": f"{base_url}/q-learning-actions/", "description": "Create a new action"},
                    {"method": "GET", "url": f"{base_url}/q-learning-actions/{{id}}/", "description": "Retrieve an action"},
                    {"method": "PUT", "url": f"{base_url}/q-learning-actions/{{id}}/", "description": "Update an action"},
                    {"method": "DELETE", "url": f"{base_url}/q-learning-actions/{{id}}/", "description": "Delete an action"}
                ]
            },
            {
                "name": "Q-Table Entries",
                "description": "CRUD operations for Q-Table entries",
                "endpoints": [
                    {"method": "GET", "url": f"{base_url}/q-table-entries/", "description": "List all Q-table entries"},
                    {"method": "POST", "url": f"{base_url}/q-table-entries/", "description": "Create a new Q-table entry"},
                    {"method": "GET", "url": f"{base_url}/q-table-entries/{{id}}/", "description": "Retrieve a Q-table entry"},
                    {"method": "PUT", "url": f"{base_url}/q-table-entries/{{id}}/", "description": "Update a Q-table entry"},
                    {"method": "DELETE", "url": f"{base_url}/q-table-entries/{{id}}/", "description": "Delete a Q-table entry"}
                ]
            },
            {
                "name": "Supplier Rankings",
                "description": "CRUD operations for supplier rankings",
                "endpoints": [
                    {"method": "GET", "url": f"{base_url}/supplier-rankings/", "description": "List all supplier rankings"},
                    {"method": "POST", "url": f"{base_url}/supplier-rankings/", "description": "Create a new ranking"},
                    {"method": "GET", "url": f"{base_url}/supplier-rankings/{{id}}/", "description": "Retrieve a ranking"},
                    {"method": "PUT", "url": f"{base_url}/supplier-rankings/{{id}}/", "description": "Update a ranking"},
                    {"method": "DELETE", "url": f"{base_url}/supplier-rankings/{{id}}/", "description": "Delete a ranking"}
                ]
            },
            {
                "name": "Supplier Performance Cache",
                "description": "CRUD operations for cached supplier performance data",
                "endpoints": [
                    {"method": "GET", "url": f"{base_url}/supplier-performance-cache/", "description": "List all performance cache entries"},
                    {"method": "POST", "url": f"{base_url}/supplier-performance-cache/", "description": "Create a new cache entry"},
                    {"method": "GET", "url": f"{base_url}/supplier-performance-cache/{{id}}/", "description": "Retrieve a cache entry"},
                    {"method": "PUT", "url": f"{base_url}/supplier-performance-cache/{{id}}/", "description": "Update a cache entry"},
                    {"method": "DELETE", "url": f"{base_url}/supplier-performance-cache/{{id}}/", "description": "Delete a cache entry"}
                ]
            },
            {
                "name": "Ranking Configuration",
                "description": "CRUD operations for ranking system configuration",
                "endpoints": [
                    {"method": "GET", "url": f"{base_url}/ranking-configurations/", "description": "List all configurations"},
                    {"method": "POST", "url": f"{base_url}/ranking-configurations/", "description": "Create a new configuration"},
                    {"method": "GET", "url": f"{base_url}/ranking-configurations/{{id}}/", "description": "Retrieve a configuration"},
                    {"method": "PUT", "url": f"{base_url}/ranking-configurations/{{id}}/", "description": "Update a configuration"},
                    {"method": "GET", "url": f"{base_url}/ranking-configurations/active_config/", "description": "Get the active configuration"}
                ]
            },
            {
                "name": "Ranking Events",
                "description": "CRUD operations for ranking events",
                "endpoints": [
                    {"method": "GET", "url": f"{base_url}/ranking-events/", "description": "List all ranking events"},
                    {"method": "POST", "url": f"{base_url}/ranking-events/", "description": "Create a new ranking event"},
                    {"method": "GET", "url": f"{base_url}/ranking-events/{{id}}/", "description": "Retrieve a ranking event"},
                    {"method": "PUT", "url": f"{base_url}/ranking-events/{{id}}/", "description": "Update a ranking event"}
                ]
            },
            # Q-Learning and Training endpoints
            {
                "name": "Q-Learning and Training",
                "description": "Endpoints for training and using Q-Learning models",
                "endpoints": [
                    {"method": "POST", "url": f"{base_url}/train-q-learning-model/", "description": "Train the Q-Learning model"},
                    {"method": "POST", "url": f"{base_url}/predict-supplier-ranking/", "description": "Predict supplier ranking using Q-Learning"}
                ]
            },
            # Analytics endpoints
            {
                "name": "Analytics",
                "description": "Endpoints for analytics and metrics",
                "endpoints": [
                    {"method": "GET", "url": f"{base_url}/supplier-metrics/{{supplier_id}}/", "description": "Get comprehensive metrics for a supplier"},
                    {"method": "GET", "url": f"{base_url}/ranking-history/", "description": "Get historical ranking data for all suppliers"},
                    {"method": "GET", "url": f"{base_url}/performance-dashboard/", "description": "Get data for the performance dashboard"}
                ]
            },
            # Recommendations and Decision Support
            {
                "name": "Recommendations",
                "description": "Endpoints for supplier recommendations and decision support",
                "endpoints": [
                    {"method": "POST", "url": f"{base_url}/supplier-recommendations/", "description": "Get supplier recommendations for a product"},
                    {"method": "POST", "url": f"{base_url}/optimal-order-allocation/", "description": "Determine optimal order allocation across suppliers"}
                ]
            },
            # Integration endpoints
            {
                "name": "Integration",
                "description": "Endpoints for integration with other groups",
                "endpoints": [
                    {"method": "POST", "url": f"{base_url}/demand-forecast-integration/", "description": "Integrate with Demand Forecasting (Group 29)"},
                    {"method": "POST", "url": f"{base_url}/blockchain-data-integration/", "description": "Integrate with Blockchain Tracking (Group 30)"},
                    {"method": "POST", "url": f"{base_url}/logistics-integration/", "description": "Integrate with Logistics (Group 32)"}
                ]
            },
            # System Management
            {
                "name": "System Management",
                "description": "Endpoints for system management",
                "endpoints": [
                    {"method": "POST", "url": f"{base_url}/reset-q-table/", "description": "Reset the Q-Learning table"},
                    {"method": "GET", "url": f"{base_url}/export-ranking-data/", "description": "Export supplier ranking data"},
                    {"method": "POST", "url": f"{base_url}/import-performance-data/", "description": "Import supplier performance data"}
                ]
            }
        ]
        
        return Response({
            "api_name": "Supplier Ranking Service API",
            "version": "1.0",
            "base_url": base_url,
            "authentication": "Token-based authentication required for most endpoints",
            "endpoints": endpoints,
            "generated_at": datetime.now().isoformat()
        })