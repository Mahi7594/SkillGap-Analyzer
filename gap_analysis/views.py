from django.shortcuts import render, redirect, get_object_or_404
import json
from .forms import DesignationForm, SkillBenchmarkForm, EmployeeForm, EmployeeSkillForm
from .models import Designation, SkillBenchmark, Employee, EmployeeSkill

def generic_add_view(request, form_class, title):
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = form_class()
    return render(request, 'gap_analysis/add_form.html', {'form': form, 'title': title})

def dashboard(request):
    employees = Employee.objects.all()
    designations = Designation.objects.all()
    
    selected_emp_id = request.GET.get('employee')
    selected_desig_id = request.GET.get('designation')
    
    selected_employee = None
    if selected_emp_id:
        selected_employee = Employee.objects.filter(id=selected_emp_id).first()
    elif employees.exists():
        selected_employee = employees.first()

    selected_designation = None
    if selected_desig_id:
        selected_designation = Designation.objects.filter(id=selected_desig_id).first()
    elif designations.exists():
        selected_designation = designations.first()

    # 1. INDIVIDUAL DATA
    ind_labels = []
    ind_actual = []
    ind_benchmark = []

    if selected_employee:
        emp_skills = EmployeeSkill.objects.filter(employee=selected_employee)
        for es in emp_skills:
            ind_labels.append(es.skill_name)
            ind_actual.append(es.actual_level)
            bm = SkillBenchmark.objects.filter(designation=selected_employee.designation, skill_name=es.skill_name).first()
            ind_benchmark.append(bm.required_level if bm else 0)

    # 2. COMPLETE TEAM DATA
    all_skills = EmployeeSkill.objects.select_related('employee__designation')
    team_stats = {}
    for es in all_skills:
        skill = es.skill_name
        if skill not in team_stats:
            team_stats[skill] = {'actual_total': 0, 'benchmark_total': 0, 'count': 0}
        team_stats[skill]['actual_total'] += es.actual_level
        team_stats[skill]['count'] += 1
        bm = SkillBenchmark.objects.filter(designation=es.employee.designation, skill_name=skill).first()
        if bm:
            team_stats[skill]['benchmark_total'] += bm.required_level

    team_labels = list(team_stats.keys())
    team_actual = [round(team_stats[s]['actual_total'] / team_stats[s]['count'], 1) for s in team_labels]
    team_benchmark = [round(team_stats[s]['benchmark_total'] / team_stats[s]['count'], 1) for s in team_labels]

    # 3. DESIGNATION DATA
    desig_labels = []
    desig_actual = []
    desig_benchmark = []

    if selected_designation:
        desig_skills = EmployeeSkill.objects.filter(employee__designation=selected_designation)
        desig_stats = {}
        for es in desig_skills:
            skill = es.skill_name
            if skill not in desig_stats:
                desig_stats[skill] = {'actual_total': 0, 'count': 0}
            desig_stats[skill]['actual_total'] += es.actual_level
            desig_stats[skill]['count'] += 1

        desig_labels = list(desig_stats.keys())
        desig_actual = [round(desig_stats[s]['actual_total'] / desig_stats[s]['count'], 1) for s in desig_labels]
        for skill in desig_labels:
            bm = SkillBenchmark.objects.filter(designation=selected_designation, skill_name=skill).first()
            desig_benchmark.append(bm.required_level if bm else 0)

    context = {
        'employees': employees,
        'selected_employee': selected_employee,
        'designations': designations,
        'selected_designation': selected_designation,
        'ind_labels': json.dumps(ind_labels),
        'ind_actual': json.dumps(ind_actual),
        'ind_benchmark': json.dumps(ind_benchmark),
        'team_labels': json.dumps(team_labels),
        'team_actual': json.dumps(team_actual),
        'team_benchmark': json.dumps(team_benchmark),
        'desig_labels': json.dumps(desig_labels),
        'desig_actual': json.dumps(desig_actual),
        'desig_benchmark': json.dumps(desig_benchmark),
    }
    return render(request, 'gap_analysis/dashboard.html', context)

# --- NEW FUNCTION FOR THE SKILL CARD ---
def employee_card(request, emp_id):
    # Fetch the employee, or return a 404 error if they don't exist
    employee = get_object_or_404(Employee, id=emp_id)
    raw_skills = EmployeeSkill.objects.filter(employee=employee)
    
    skill_details = []
    
    for es in raw_skills:
        # Find the benchmark
        bm = SkillBenchmark.objects.filter(designation=employee.designation, skill_name=es.skill_name).first()
        req_level = bm.required_level if bm else 0
        
        # Calculate the mathematical gap
        gap = req_level - es.actual_level
        
        # Determine the status for our CSS styling
        if gap <= 0:
            status = 'proficient'
            gap_text = "Meets Benchmark"
        else:
            status = 'gap'
            gap_text = f"Gap: -{gap} Level(s)"
            
        skill_details.append({
            'name': es.skill_name,
            'actual': es.actual_level,
            'required': req_level,
            'status': status,
            'gap_text': gap_text
        })
        
    return render(request, 'gap_analysis/employee_card.html', {
        'employee': employee,
        'skill_details': skill_details
    })

def add_designation(request):
    return generic_add_view(request, DesignationForm, 'Add Designation')
def add_benchmark(request):
    return generic_add_view(request, SkillBenchmarkForm, 'Add Skill Benchmark')
def add_employee(request):
    return generic_add_view(request, EmployeeForm, 'Add Employee')
def add_employee_skill(request):
    return generic_add_view(request, EmployeeSkillForm, 'Add Employee Skill')