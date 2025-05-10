from rest_framework import serializers
from .models import (
    QLearningState,
    QLearningAction,
    QTableEntry,
    SupplierRanking,
    SupplierPerformanceCache,
    RankingConfiguration,
    RankingEvent
)


class QLearningStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QLearningState
        fields = '__all__'


class QLearningActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QLearningAction
        fields = '__all__'


class QTableEntrySerializer(serializers.ModelSerializer):
    state_name = serializers.StringRelatedField(source='state')
    action_name = serializers.StringRelatedField(source='action')
    
    class Meta:
        model = QTableEntry
        fields = '__all__'


class SupplierRankingSerializer(serializers.ModelSerializer):
    state_name = serializers.StringRelatedField(source='state')
    compliance_score = serializers.SerializerMethodField()
    
    class Meta:
        model = SupplierRanking
        fields = '__all__'
    
    def get_compliance_score(self, obj):
        """Get the compliance score from the performance cache or user service"""
        try:
            # First try to get from performance cache
            cache = SupplierPerformanceCache.objects.filter(
                supplier_id=obj.supplier_id,
                date=obj.date
            ).first()
            
            if cache and cache.compliance_score is not None:
                return cache.compliance_score
                
            # If not in cache, try to get from user service
            from connectors.user_service_connector import UserServiceConnector
            user_service = UserServiceConnector()
            supplier = user_service.get_supplier_by_id(obj.supplier_id)
            
            if supplier:
                return supplier.get('compliance_score', 5.0)
                
            return 5.0  # Default value if not found
        except Exception:
            return 5.0  # Default value on error


class SupplierPerformanceCacheSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierPerformanceCache
        fields = '__all__'


class RankingConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RankingConfiguration
        fields = '__all__'


class RankingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RankingEvent
        fields = '__all__'


# Custom serializers for specific API endpoints
class SupplierRankingInputSerializer(serializers.Serializer):
    supplier_id = serializers.IntegerField(required=False, help_text="Filter by supplier ID")
    start_date = serializers.DateField(required=False, help_text="Start date for ranking period")
    end_date = serializers.DateField(required=False, help_text="End date for ranking period")
    metrics = serializers.MultipleChoiceField(
        choices=[
            'quality', 
            'delivery', 
            'price', 
            'service'
        ],
        required=False,
        help_text="Metrics to include in ranking calculation"
    )


class TrainQLearningModelSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=True, help_text="Start date for training data")
    end_date = serializers.DateField(required=True, help_text="End date for training data")
    learning_rate = serializers.FloatField(required=False, help_text="Learning rate (alpha) for Q-Learning algorithm")
    discount_factor = serializers.FloatField(required=False, help_text="Discount factor (gamma) for Q-Learning algorithm")
    exploration_rate = serializers.FloatField(required=False, help_text="Exploration rate (epsilon) for Q-Learning algorithm")
    iterations = serializers.IntegerField(required=False, help_text="Number of iterations for training")


class SupplierMetricsSerializer(serializers.Serializer):
    supplier_id = serializers.IntegerField(required=True, help_text="Supplier ID")
    start_date = serializers.DateField(required=False, help_text="Start date for metrics")
    end_date = serializers.DateField(required=False, help_text="End date for metrics")
    
    # Output fields (read-only)
    avg_quality_score = serializers.FloatField(read_only=True)
    avg_defect_rate = serializers.FloatField(read_only=True)
    avg_on_time_delivery_rate = serializers.FloatField(read_only=True)
    avg_price_competitiveness = serializers.FloatField(read_only=True)
    avg_responsiveness = serializers.FloatField(read_only=True)
    avg_fill_rate = serializers.FloatField(read_only=True)
    avg_order_accuracy = serializers.FloatField(read_only=True)
    current_rank = serializers.IntegerField(read_only=True)
    rank_trend = serializers.ListField(child=serializers.IntegerField(), read_only=True)


class SupplierRecommendationSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True, help_text="Product ID for which to recommend suppliers")
    quantity = serializers.IntegerField(required=True, help_text="Quantity needed")
    delivery_date = serializers.DateField(required=True, help_text="Required delivery date")
    
    # Optional parameters for fine-tuning recommendations
    prioritize_quality = serializers.BooleanField(required=False, default=False, help_text="Prioritize quality over price")
    prioritize_delivery = serializers.BooleanField(required=False, default=False, help_text="Prioritize delivery reliability over price")
    
    # Output fields (read-only)
    recommended_suppliers = serializers.ListField(child=serializers.DictField(), read_only=True)
    recommendation_explanation = serializers.CharField(read_only=True)


class SupplierPerformanceDetailSerializer(serializers.Serializer):
    supplier_id = serializers.IntegerField(required=True, help_text="Supplier ID")
    date = serializers.DateField(required=False, help_text="Performance date (defaults to latest)")
    
    # Output fields (read-only)
    supplier_name = serializers.CharField(read_only=True)
    quality_metrics = serializers.DictField(read_only=True)
    delivery_metrics = serializers.DictField(read_only=True)
    price_metrics = serializers.DictField(read_only=True)
    service_metrics = serializers.DictField(read_only=True)
    fulfillment_metrics = serializers.DictField(read_only=True)
    compliance_metrics = serializers.DictField(read_only=True)
    overall_rank = serializers.IntegerField(read_only=True)
    historical_performance = serializers.ListField(child=serializers.DictField(), read_only=True)


class RankingComparisonSerializer(serializers.Serializer):
    supplier_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        help_text="List of supplier IDs to compare"
    )
    date = serializers.DateField(required=False, help_text="Date for comparison (defaults to latest)")
    metrics = serializers.MultipleChoiceField(
        choices=[
            'quality', 
            'delivery', 
            'price', 
            'service',
            'compliance',
            'forecast_accuracy',
            'logistics'
        ],
        required=False,
        help_text="Metrics to include in comparison"
    )
    
    # Output fields (read-only)
    comparison_results = serializers.ListField(child=serializers.DictField(), read_only=True)
    recommendation = serializers.CharField(read_only=True)