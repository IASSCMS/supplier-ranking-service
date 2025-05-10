from django.urls import path
from .api_views import (
    FeedbackView,
    SupplierRankingView,
    ManualTrainingView,
    QValueView,
    QTableView
)

app_name = 'ranking_engine'  # Add app namespace

urlpatterns = [
    # Core API endpoints for Q-Learning based supplier ranking
    path('feedback/', FeedbackView.as_view(), name='feedback'),
    path('ranking/suppliers/', SupplierRankingView.as_view(), name='ranking_suppliers'),
    path('train/manual/', ManualTrainingView.as_view(), name='train_manual'),
    path('qvalue/', QValueView.as_view(), name='qvalue'),
    path('qtable/', QTableView.as_view(), name='qtable'),
] 