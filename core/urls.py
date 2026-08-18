from django.urls import path
from . import views

urlpatterns = [
    # Dashboard (Main Overview)
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # History & Audit Logs
    path('history/', views.history_view, name='history'),
    path('history/export/csv/', views.export_logs_csv, name='export_logs_csv'),
    path('history/export/json/', views.export_logs_json, name='export_logs_json'),

    # Pricing Tiers Matrix
    path('pricing/', views.pricing_view, name='pricing'),

    # Monthly Invoices
    path('invoices/', views.invoices_view, name='invoices'),
    path('invoices/generate', views.generate_invoice, name='generate_invoice')
]
