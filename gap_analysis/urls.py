from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Create URLs
    path('add-designation/', views.RoleMatrixCreateView.as_view(), name='add_designation'),
    path('add-benchmark/', views.SkillBenchmarkCreateView.as_view(), name='add_benchmark'),
    path('add-employee/', views.SkillMatrixCreateView.as_view(), name='add_employee'),
    path('create-skill/', views.SkillCreateView.as_view(), name='add_skill'),
    path('add-skill/', views.EmployeeSkillCreateView.as_view(), name='add_employee_skill'),
    
    # Employee URLs
    path('employees/', views.SkillMatrixListView.as_view(), name='employee_list'),
    path('employee/<int:pk>/', views.SkillMatrixProfileView.as_view(), name='employee_profile'),
    path('employee/<int:pk>/edit/', views.SkillMatrixUpdateView.as_view(), name='employee_update'),
    path('employee/<int:pk>/delete/', views.SkillMatrixDeleteView.as_view(), name='employee_delete'),
    path('employee/<int:pk>/skill-update/', views.employee_skill_update, name='employee_skill_update'),
    path('employee/<int:emp_id>/card/', views.SkillMatrixCardView.as_view(), name='employee_card'),
    
    # Skills URLs
    path('skills/', views.SkillListView.as_view(), name='skill_list'),
    path('skills/<int:pk>/edit/', views.SkillUpdateView.as_view(), name='skill_update'),
    path('skills/<int:pk>/delete/', views.SkillDeleteView.as_view(), name='skill_delete'),
    
    # Role Matrix URLs
    path('designations/', views.RoleMatrixListView.as_view(), name='designation_list'),
    path('designations/<int:pk>/edit/', views.RoleMatrixUpdateView.as_view(), name='designation_update'),
    path('designations/<int:pk>/delete/', views.RoleMatrixDeleteView.as_view(), name='designation_delete'),
    
    # Benchmarks & Employee Skills
    path('benchmarks/', views.BenchmarkListView.as_view(), name='benchmark_list'),
    path('employee-skills/', views.EmployeeSkillListView.as_view(), name='employee_skill_list'),
    
    # Designation Benchmark Management
    path('designations/<int:pk>/benchmarks/', views.RoleMatrixBenchmarkView.as_view(), name='designation_benchmark'),
    path('designations/<int:pk>/benchmarks/add/', views.RoleMatrixBenchmarkAddView.as_view(), name='designation_benchmark_add'),
    path('designations/benchmark/<int:pk>/delete/', views.RoleMatrixBenchmarkDeleteView.as_view(), name='designation_benchmark_delete'),
]