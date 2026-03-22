from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add-designation/', views.add_designation, name='add_designation'),
    path('add-benchmark/', views.add_benchmark, name='add_benchmark'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('create-skill/', views.add_skill, name='add_skill'),
    path('add-skill/', views.add_employee_skill, name='add_employee_skill'),
    # New dynamic URL for the employee card
    path('employee/<int:emp_id>/', views.employee_card, name='employee_card'), 
    path('skills/', views.skill_list, name='skill_list'),
    path('skills/<int:pk>/edit/', views.skill_update, name='skill_update'),
    path('skills/<int:pk>/delete/', views.skill_delete, name='skill_delete'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/<int:pk>/edit/', views.employee_update, name='employee_update'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('designations/', views.designation_list, name='designation_list'),
    path('designations/<int:pk>/edit/', views.designation_update, name='designation_update'),
    path('designations/<int:pk>/delete/', views.designation_delete, name='designation_delete'),
]