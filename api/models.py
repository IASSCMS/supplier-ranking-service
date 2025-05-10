from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class QLearningState(models.Model):
    """Model for storing states used in Q-Learning"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    
    def __str__(self):
        return self.name


class QLearningAction(models.Model):
    """Model for storing actions used in Q-Learning"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    
    def __str__(self):
        return self.name


class QTableEntry(models.Model):
    """Model for storing Q-values for state-action pairs"""
    
    state = models.ForeignKey(QLearningState, on_delete=models.CASCADE, related_name='q_values')
    action = models.ForeignKey(QLearningAction, on_delete=models.CASCADE, related_name='q_values')
    q_value = models.FloatField(default=0.0)
    update_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('state', 'action')
    
    def __str__(self):
        return f"{self.state.name} - {self.action.name}: {self.q_value}"


class SupplierRanking(models.Model):
    """Model for storing supplier rankings"""
    
    supplier_id = models.IntegerField(default=0, help_text="ID reference to Supplier in User Service")
    supplier_name = models.CharField(max_length=255, default="Unknown Supplier", help_text="Cached supplier name for display purposes")
    date = models.DateField()
    overall_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    quality_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    delivery_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    price_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    service_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    rank = models.IntegerField(help_text="Rank position among all suppliers")
    tier = models.IntegerField(default=3, help_text="Supplier tier level (1-3, with 1 being highest)")
    state = models.ForeignKey(QLearningState, on_delete=models.SET_NULL, null=True, related_name='supplier_rankings')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('supplier_id', 'date')
    
    def __str__(self):
        return f"{self.supplier_name} - Rank {self.rank} on {self.date}"


class SupplierPerformanceCache(models.Model):
    """
    Cached performance data from other services for use in ranking calculations
    This prevents too many API calls during ranking calculations
    """
    
    supplier_id = models.IntegerField(help_text="ID reference to Supplier in User Service")
    supplier_name = models.CharField(max_length=255)
    date = models.DateField()
    
    # Quality metrics from Order Management Service
    quality_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    defect_rate = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    return_rate = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Delivery metrics from Order Management Service and Blockchain Service
    on_time_delivery_rate = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    average_delay_days = models.FloatField(default=0)
    
    # Price metrics from Warehouse Management Service
    price_competitiveness = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    
    # Service metrics from various services
    responsiveness = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    issue_resolution_time = models.FloatField(help_text="Average time to resolve issues in hours", null=True, blank=True)
    
    # Fulfillment metrics from Order Management Service
    fill_rate = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)],
                                 help_text="Percentage of order quantities fulfilled")
    order_accuracy = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)],
                                     help_text="Percentage of orders with correct items")
    
    # Compliance metrics from User Service
    compliance_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)], 
                                        null=True, blank=True)
    
    # Data from demand forecasting (Group 29)
    demand_forecast_accuracy = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)], 
                                                null=True, blank=True)
    
    # Data from logistics (Group 32)
    logistics_efficiency = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)], 
                                           null=True, blank=True)
    
    # Metadata about the cache
    last_updated = models.DateTimeField(auto_now=True)
    data_complete = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('supplier_id', 'date')
    
    def __str__(self):
        return f"{self.supplier_name} Performance Cache - {self.date}"


class RankingConfiguration(models.Model):
    """Model for storing configuration parameters for the ranking system"""
    
    name = models.CharField(max_length=100, unique=True)
    learning_rate = models.FloatField(default=0.1)
    discount_factor = models.FloatField(default=0.9)
    exploration_rate = models.FloatField(default=0.3)
    quality_weight = models.FloatField(default=0.25)
    delivery_weight = models.FloatField(default=0.25)
    price_weight = models.FloatField(default=0.25)
    service_weight = models.FloatField(default=0.25)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


class RankingEvent(models.Model):
    """Model for logging ranking events and decisions"""
    
    EVENT_TYPES = (
        ('RANKING_STARTED', 'Ranking Process Started'),
        ('RANKING_COMPLETED', 'Ranking Process Completed'),
        ('MODEL_TRAINED', 'Q-Learning Model Trained'),
        ('RECOMMENDATION_MADE', 'Supplier Recommendation Made'),
        ('DATA_FETCHED', 'External Data Fetched'),
        ('ERROR', 'Error Occurred'),
    )
    
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    supplier_id = models.IntegerField(null=True, blank=True)
    state_id = models.IntegerField(null=True, blank=True)
    action_id = models.IntegerField(null=True, blank=True)
    reward = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.event_type} - {self.timestamp}"