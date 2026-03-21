from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add-designation/', views.add_designation, name='add_designation'),
    path('add-benchmark/', views.add_benchmark, name='add_benchmark'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('add-skill/', views.add_employee_skill, name='add_employee_skill'),
    # New dynamic URL for the employee card
    path('employee/<int:emp_id>/', views.employee_card, name='employee_card'), 
]