from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, DetailView, ListView, CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.http import JsonResponse
import json

from .forms import RoleMatrixForm, SkillBenchmarkForm, SkillMatrixForm, EmployeeSkillForm, SkillForm, RoleMatrixBenchmarkForm
from .models import RoleMatrix, SkillBenchmark, SkillMatrix, EmployeeSkill, Skill

class DashboardView(TemplateView):
    template_name = 'gap_analysis/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        
        employees = SkillMatrix.objects.all()
        designations = RoleMatrix.objects.all()
        
        selected_emp_id = request.GET.get('employee')
        selected_desig_id = request.GET.get('designation')
        
        selected_employee = None
        if selected_emp_id:
            selected_employee = SkillMatrix.objects.filter(id=selected_emp_id).first()
        elif employees.exists():
            selected_employee = employees.first()

        selected_designation = None
        if selected_desig_id:
            selected_designation = RoleMatrix.objects.filter(id=selected_desig_id).first()
        elif designations.exists():
            selected_designation = designations.first()

        # 1. INDIVIDUAL DATA
        ind_labels, ind_actual, ind_benchmark = [], [], []
        if selected_employee:
            emp_skills = EmployeeSkill.objects.filter(skill_matrix=selected_employee, skill__isnull=False).select_related('skill')
            for es in emp_skills:
                ind_labels.append(es.skill.name)
                ind_actual.append(es.actual_level)
                bm = SkillBenchmark.objects.filter(role_matrix=selected_employee.role_matrix, skill=es.skill).first()
                ind_benchmark.append(bm.required_level if bm else 0)

        # 2. COMPLETE TEAM DATA
        all_skills = EmployeeSkill.objects.filter(skill__isnull=False).select_related('skill_matrix__role_matrix', 'skill')
        team_stats = {}
        for es in all_skills:
            skill = es.skill.name
            if skill not in team_stats:
                team_stats[skill] = {'actual_total': 0, 'benchmark_total': 0, 'count': 0}
            team_stats[skill]['actual_total'] += es.actual_level
            team_stats[skill]['count'] += 1
            bm = SkillBenchmark.objects.filter(role_matrix=es.skill_matrix.role_matrix, skill=es.skill).first()
            if bm:
                team_stats[skill]['benchmark_total'] += bm.required_level

        team_labels = list(team_stats.keys())
        team_actual = [round(team_stats[s]['actual_total'] / team_stats[s]['count'], 1) for s in team_labels]
        team_benchmark = [round(team_stats[s]['benchmark_total'] / team_stats[s]['count'], 1) for s in team_labels]

        # 3. DESIGNATION DATA
        desig_labels, desig_actual, desig_benchmark = [], [], []
        if selected_designation:
            desig_skills = EmployeeSkill.objects.filter(skill_matrix__role_matrix=selected_designation, skill__isnull=False).select_related('skill')
            desig_stats = {}
            for es in desig_skills:
                skill = es.skill.name
                if skill not in desig_stats:
                    desig_stats[skill] = {'actual_total': 0, 'count': 0}
                desig_stats[skill]['actual_total'] += es.actual_level
                desig_stats[skill]['count'] += 1

            desig_labels = list(desig_stats.keys())
            desig_actual = [round(desig_stats[s]['actual_total'] / desig_stats[s]['count'], 1) for s in desig_labels]
            for skill in desig_labels:
                bm = SkillBenchmark.objects.filter(role_matrix=selected_designation, skill__name=skill).first()
                desig_benchmark.append(bm.required_level if bm else 0)

        # KPI Metrics
        total_employees = employees.count()
        total_skills = Skill.objects.count()
        
        # Calculate average gap score and skills met percentage
        all_emp_skills = EmployeeSkill.objects.filter(skill__isnull=False).select_related('skill_matrix__role_matrix', 'skill')
        total_gap = 0
        skills_comparison_count = 0
        skills_met_count = 0
        
        for es in all_emp_skills:
            bm = SkillBenchmark.objects.filter(role_matrix=es.skill_matrix.role_matrix, skill=es.skill).first()
            if bm:
                gap = bm.required_level - es.actual_level
                total_gap += gap
                skills_comparison_count += 1
                if gap <= 0:
                    skills_met_count += 1
        
        avg_gap_score = round(total_gap / skills_comparison_count, 1) if skills_comparison_count > 0 else 0
        skills_met_percent = round((skills_met_count / skills_comparison_count) * 100) if skills_comparison_count > 0 else 0
        
        # === NEW INSIGHTS ===
        
        # 1. Role Gap Summary - average gap per role
        role_gap_data = []
        for role in designations:
            role_skills = EmployeeSkill.objects.filter(
                skill_matrix__role_matrix=role,
                skill__isnull=False
            ).select_related('skill')
            
            if role_skills.exists():
                role_total_gap = 0
                role_count = 0
                for es in role_skills:
                    bm = SkillBenchmark.objects.filter(role_matrix=role, skill=es.skill).first()
                    if bm:
                        role_total_gap += (bm.required_level - es.actual_level)
                        role_count += 1
                
                avg_role_gap = round(role_total_gap / role_count, 2) if role_count > 0 else 0
                role_gap_data.append({
                    'role': role.title,
                    'department': role.department or '-',
                    'avg_gap': avg_role_gap,
                    'employee_count': role_skills.values('skill_matrix').distinct().count(),
                })
        
        # 2. Top Skill Gaps - employees with highest total gaps
        top_gap_employees = []
        for emp in employees:
            emp_skills = EmployeeSkill.objects.filter(
                skill_matrix=emp,
                skill__isnull=False
            ).select_related('skill')
            
            total_gap = 0
            gap_count = 0
            for es in emp_skills:
                bm = SkillBenchmark.objects.filter(role_matrix=emp.role_matrix, skill=es.skill).first()
                if bm:
                    gap = bm.required_level - es.actual_level
                    if gap > 0:
                        total_gap += gap
                        gap_count += 1
            
            if gap_count > 0:
                top_gap_employees.append({
                    'name': emp.name,
                    'role': emp.role_matrix.title if emp.role_matrix else '-',
                    'total_gap': total_gap,
                    'gap_count': gap_count,
                })
        
        top_gap_employees = sorted(top_gap_employees, key=lambda x: x['total_gap'], reverse=True)[:5]
        
        # 3. Critical Gaps - employees with gap > 2
        critical_gaps = []
        for emp in employees:
            emp_skills = EmployeeSkill.objects.filter(
                skill_matrix=emp,
                skill__isnull=False
            ).select_related('skill')
            
            critical_count = 0
            critical_skills = []
            for es in emp_skills:
                bm = SkillBenchmark.objects.filter(role_matrix=emp.role_matrix, skill=es.skill).first()
                if bm:
                    gap = bm.required_level - es.actual_level
                    if gap > 2:
                        critical_count += 1
                        critical_skills.append(es.skill.name)
            
            if critical_count > 0:
                critical_gaps.append({
                    'name': emp.name,
                    'role': emp.role_matrix.title if emp.role_matrix else '-',
                    'critical_count': critical_count,
                    'skills': critical_skills[:3],
                })
        
        critical_gaps = sorted(critical_gaps, key=lambda x: x['critical_count'], reverse=True)[:5]
        
        # 4. Top Performers - employees exceeding benchmark requirements
        top_performers = []
        for emp in employees:
            emp_skills = EmployeeSkill.objects.filter(
                skill_matrix=emp,
                skill__isnull=False
            ).select_related('skill')
            
            exceed_count = 0
            total_evaluated = 0
            for es in emp_skills:
                bm = SkillBenchmark.objects.filter(role_matrix=emp.role_matrix, skill=es.skill).first()
                if bm:
                    total_evaluated += 1
                    if es.actual_level >= bm.required_level:
                        exceed_count += 1
            
            if total_evaluated > 0:
                top_performers.append({
                    'name': emp.name,
                    'role': emp.role_matrix.title if emp.role_matrix else '-',
                    'exceed_count': exceed_count,
                    'total_evaluated': total_evaluated,
                    'exceed_percent': round((exceed_count / total_evaluated) * 100),
                })
        
        top_performers = sorted(top_performers, key=lambda x: x['exceed_percent'], reverse=True)[:5]
        
        # 5. Skills Needing Training - skills with highest gaps across org
        skill_gaps = {}
        all_es = EmployeeSkill.objects.filter(skill__isnull=False).select_related('skill', 'skill_matrix__role_matrix')
        for es in all_es:
            bm = SkillBenchmark.objects.filter(role_matrix=es.skill_matrix.role_matrix, skill=es.skill).first()
            if bm:
                gap = bm.required_level - es.actual_level
                if gap > 0:
                    if es.skill.name not in skill_gaps:
                        skill_gaps[es.skill.name] = {'total_gap': 0, 'count': 0, 'category': es.skill.category}
                    skill_gaps[es.skill.name]['total_gap'] += gap
                    skill_gaps[es.skill.name]['count'] += 1
        
        skills_needing_training = []
        for skill_name, data in skill_gaps.items():
            avg_gap = round(data['total_gap'] / data['count'], 2)
            skills_needing_training.append({
                'skill': skill_name,
                'category': data['category'] or '-',
                'avg_gap': avg_gap,
                'affected_count': data['count'],
            })
        
        skills_needing_training = sorted(skills_needing_training, key=lambda x: x['avg_gap'], reverse=True)[:5]
        
        # 6. Benchmark Compliance - % of employees meeting benchmarks
        compliance_stats = {'meeting': 0, 'partial': 0, 'needs_training': 0, 'total': 0}
        for emp in employees:
            emp_skills = EmployeeSkill.objects.filter(
                skill_matrix=emp,
                skill__isnull=False
            ).select_related('skill')
            
            if not emp_skills.exists():
                continue
                
            compliance_stats['total'] += 1
            met_count = 0
            gap_count = 0
            for es in emp_skills:
                bm = SkillBenchmark.objects.filter(role_matrix=emp.role_matrix, skill=es.skill).first()
                if bm:
                    if es.actual_level >= bm.required_level:
                        met_count += 1
                    elif bm.required_level - es.actual_level > 1:
                        gap_count += 1
            
            if met_count == 0 and gap_count > 0:
                compliance_stats['needs_training'] += 1
            elif met_count > 0 and gap_count == 0:
                compliance_stats['meeting'] += 1
            else:
                compliance_stats['partial'] += 1
        
        # Calculate percentages
        if compliance_stats['total'] > 0:
            compliance_stats['meeting_pct'] = round((compliance_stats['meeting'] / compliance_stats['total']) * 100)
            compliance_stats['partial_pct'] = round((compliance_stats['partial'] / compliance_stats['total']) * 100)
            compliance_stats['needs_training_pct'] = round((compliance_stats['needs_training'] / compliance_stats['total']) * 100)
        else:
            compliance_stats['meeting_pct'] = 0
            compliance_stats['partial_pct'] = 0
            compliance_stats['needs_training_pct'] = 0
        
        # 7. Skill Distribution by Category
        skill_category_dist = {}
        for cat in Skill.CATEGORY_CHOICES:
            count = Skill.objects.filter(category=cat[0]).count()
            if count > 0:
                skill_category_dist[cat[1]] = count
        skill_category_dist['Uncategorized'] = Skill.objects.filter(category__isnull=True).count()

        context.update({
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
            'total_employees': total_employees,
            'total_skills': total_skills,
            'avg_gap_score': avg_gap_score,
            'skills_met': skills_met_percent,
            # New insights
            'role_gap_data': role_gap_data,
            'top_gap_employees': top_gap_employees,
            'critical_gaps': critical_gaps,
            'top_performers': top_performers,
            'skills_needing_training': skills_needing_training,
            'compliance_stats': compliance_stats,
            'skill_category_dist': skill_category_dist,
        })
        return context

class SkillMatrixCardView(DetailView):
    model = SkillMatrix
    template_name = 'gap_analysis/employee_card.html'
    pk_url_kwarg = 'emp_id'
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.object
        
        benchmarks = SkillBenchmark.objects.filter(role_matrix=skill_matrix.role_matrix).select_related('skill')
        
        skill_details = []
        for bm in benchmarks:
            emp_skill = EmployeeSkill.objects.filter(skill_matrix=employee, skill=bm.skill).first()
            actual_level = emp_skill.actual_level if emp_skill else 0
            gap = bm.required_level - actual_level
            
            if gap <= 0:
                status = 'proficient'
            elif gap <= 1:
                status = 'warning'
            else:
                status = 'gap'
                
            skill_details.append({
                'name': bm.skill.name,
                'actual': actual_level,
                'required': bm.required_level,
                'gap': gap,
                'status': status,
            })
            
        context['skill_details'] = skill_details
        return context

# --- CREATE VIEWS ---
class RoleMatrixCreateView(SuccessMessageMixin, CreateView):
    model = RoleMatrix
    form_class = RoleMatrixForm
    template_name = 'gap_analysis/add_form.html'
    success_url = reverse_lazy('dashboard')
    success_message = "RoleMatrix created successfully!"
    extra_context = {'title': 'Add RoleMatrix'}

class SkillBenchmarkCreateView(SuccessMessageMixin, CreateView):
    model = SkillBenchmark
    form_class = SkillBenchmarkForm
    template_name = 'gap_analysis/add_form.html'
    success_url = reverse_lazy('dashboard')
    success_message = "Skill benchmark created successfully!"
    extra_context = {'title': 'Add Skill Benchmark'}

class SkillMatrixCreateView(SuccessMessageMixin, CreateView):
    model = SkillMatrix
    form_class = SkillMatrixForm
    template_name = 'gap_analysis/add_form.html'
    success_url = reverse_lazy('dashboard')
    success_message = "Skill Matrix created successfully!"
    extra_context = {'title': 'Add Employee'}

class EmployeeSkillCreateView(SuccessMessageMixin, CreateView):
    model = EmployeeSkill
    form_class = EmployeeSkillForm
    template_name = 'gap_analysis/add_form.html'
    success_url = reverse_lazy('dashboard')
    success_message = "Employee skill recorded successfully!"
    extra_context = {'title': 'Add Employee Skill'}

class SkillCreateView(SuccessMessageMixin, CreateView):
    model = Skill
    form_class = SkillForm
    template_name = 'gap_analysis/add_form.html'
    success_url = reverse_lazy('dashboard')
    success_message = "Skill created successfully!"
    extra_context = {'title': 'Add Skill'}

# --- SKILL CRUD VIEWS ---
class SkillListView(ListView):
    model = Skill
    template_name = 'gap_analysis/skill_list.html'
    context_object_name = 'skills'
    ordering = ['name']

class SkillUpdateView(SuccessMessageMixin, UpdateView):
    model = Skill
    form_class = SkillForm
    template_name = 'gap_analysis/add_form.html'
    success_url = reverse_lazy('skill_list')
    success_message = "Skill updated successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Skill: {self.object.name}'
        return context

class SkillDeleteView(SuccessMessageMixin, DeleteView):
    model = Skill
    template_name = 'gap_analysis/skill_confirm_delete.html'
    success_url = reverse_lazy('skill_list')
    success_message = "Skill deleted successfully!"

# --- EMPLOYEE CRUD VIEWS ---
class SkillMatrixListView(ListView):
    model = SkillMatrix
    template_name = 'gap_analysis/employee_list.html'
    context_object_name = 'employees'
    queryset = SkillMatrix.objects.select_related('role_matrix').all().order_by('name')

class SkillMatrixUpdateView(SuccessMessageMixin, UpdateView):
    model = SkillMatrix
    form_class = SkillMatrixForm
    template_name = 'gap_analysis/add_form.html'
    success_url = reverse_lazy('employee_list')
    success_message = "Employee updated successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Employee: {self.object.name}'
        return context

class SkillMatrixDeleteView(SuccessMessageMixin, DeleteView):
    model = SkillMatrix
    template_name = 'gap_analysis/employee_confirm_delete.html'
    success_url = reverse_lazy('employee_list')
    success_message = "Employee deleted successfully!"

# --- DESIGNATION CRUD VIEWS ---
class RoleMatrixListView(ListView):
    model = RoleMatrix
    template_name = 'gap_analysis/designation_list.html'
    context_object_name = 'designations'
    ordering = ['title']

class RoleMatrixUpdateView(SuccessMessageMixin, UpdateView):
    model = RoleMatrix
    form_class = RoleMatrixForm
    template_name = 'gap_analysis/add_form.html'
    success_url = reverse_lazy('designation_list')
    success_message = "RoleMatrix updated successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit RoleMatrix: {self.object.title}'
        return context

class RoleMatrixDeleteView(SuccessMessageMixin, DeleteView):
    model = RoleMatrix
    template_name = 'gap_analysis/designation_confirm_delete.html'
    success_url = reverse_lazy('designation_list')
    success_message = "RoleMatrix deleted successfully!"

# --- BENCHMARK & EMPLOYEE SKILL LIST VIEWS ---
class BenchmarkListView(ListView):
    model = SkillBenchmark
    template_name = 'gap_analysis/benchmark_list.html'
    context_object_name = 'benchmarks'
    queryset = SkillBenchmark.objects.select_related('role_matrix', 'skill').all()

class BenchmarkDeleteView(SuccessMessageMixin, DeleteView):
    model = SkillBenchmark
    template_name = 'gap_analysis/benchmark_confirm_delete.html'
    success_message = "Benchmark deleted successfully!"
    
    def get_success_url(self):
        return reverse('designation_benchmark', kwargs={'pk': self.object.role_matrix.pk})

class EmployeeSkillListView(ListView):
    model = EmployeeSkill
    template_name = 'gap_analysis/employee_skill_list.html'
    context_object_name = 'employee_skills'
    queryset = EmployeeSkill.objects.select_related('skill_matrix', 'skill').all().order_by('-last_evaluated')

class EmployeeSkillDeleteView(SuccessMessageMixin, DeleteView):
    model = EmployeeSkill
    template_name = 'gap_analysis/employee_skill_confirm_delete.html'
    success_url = reverse_lazy('dashboard')
    success_message = "Employee skill deleted successfully!"

# --- EMPLOYEE PROFILE VIEWS ---
class SkillMatrixProfileView(DetailView):
    model = SkillMatrix
    template_name = 'gap_analysis/employee_profile.html'
    pk_url_kwarg = 'pk'
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.object
        
        benchmarks = employee.get_required_benchmarks()
        
        skill_data = []
        for benchmark in benchmarks:
            emp_skill = EmployeeSkill.objects.filter(skill_matrix=employee, skill=benchmark.skill).first()
            actual_level = emp_skill.actual_level if emp_skill else 0
            gap = benchmark.required_level - actual_level
            
            skill_data.append({
                'benchmark_id': benchmark.id,
                'skill_id': benchmark.skill.id,
                'skill_name': benchmark.skill.name,
                'skill_category': benchmark.skill.category,
                'required_level': benchmark.required_level,
                'actual_level': actual_level,
                'gap': gap,
                'status': 'met' if gap <= 0 else ('warning' if gap <= 1 else 'critical'),
                'is_mandatory': benchmark.is_mandatory,
                'emp_skill_id': emp_skill.id if emp_skill else None,
            })
        
        # Sort by gap (critical first)
        skill_data.sort(key=lambda x: (0 if x['gap'] > 0 else 1, -x['gap']))
        
        context['skill_data'] = skill_data
        context['skills_met'] = employee.get_skills_met_percentage()
        context['overall_gap'] = employee.get_overall_gap_score()
        
        # Chart data
        context['chart_labels'] = json.dumps([s['skill_name'] for s in skill_data])
        context['chart_actual'] = json.dumps([s['actual_level'] for s in skill_data])
        context['chart_required'] = json.dumps([s['required_level'] for s in skill_data])
        
        return context


def employee_skill_update(request, pk):
    """AJAX view to update employee skill level"""
    if request.method == 'POST':
        skill_matrix = get_object_or_404(SkillMatrix, pk=pk)
        skill_id = request.POST.get('skill_id')
        actual_level = int(request.POST.get('actual_level', 0))
        
        if skill_id:
            skill = get_object_or_404(Skill, id=skill_id)
            emp_skill, created = EmployeeSkill.objects.update_or_create(
                skill_matrix=skill_matrix,
                skill=skill,
                defaults={'actual_level': actual_level}
            )
            
            benchmark = SkillBenchmark.objects.filter(role_matrix=skill_matrix.role_matrix, skill=skill).first()
            required = benchmark.required_level if benchmark else 0
            gap = required - actual_level
            
            return JsonResponse({
                'success': True,
                'emp_skill_id': emp_skill.id,
                'actual_level': actual_level,
                'required_level': required,
                'gap': gap,
                'status': 'met' if gap <= 0 else ('warning' if gap <= 1 else 'critical'),
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


class SkillMatrixProfileUpdateView(SuccessMessageMixin, UpdateView):
    model = SkillMatrix
    form_class = SkillMatrixForm
    template_name = 'gap_analysis/employee_profile.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('employee_list')
    success_message = "Employee updated successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit_mode'] = True
        return context


# --- DESIGNATION BENCHMARK MANAGEMENT ---
class RoleMatrixBenchmarkView(TemplateView):
    template_name = 'gap_analysis/designation_benchmark.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        designation = get_object_or_404(RoleMatrix, pk=self.kwargs['pk'])
        benchmarks = SkillBenchmark.objects.filter(role_matrix=designation).select_related('skill')
        
        context['designation'] = designation
        context['benchmarks'] = benchmarks
        context['benchmark_count'] = benchmarks.count()
        return context


class RoleMatrixBenchmarkAddView(SuccessMessageMixin, CreateView):
    model = SkillBenchmark
    form_class = RoleMatrixBenchmarkForm
    template_name = 'gap_analysis/add_form.html'
    success_message = "Skill benchmark added successfully!"
    
    def get_success_url(self):
        return reverse('designation_benchmark', kwargs={'pk': self.kwargs['pk']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        designation = get_object_or_404(RoleMatrix, pk=self.kwargs['pk'])
        context['title'] = f'Add Skill to {designation.title}'
        context['designation'] = designation
        context['existing_skills'] = Skill.objects.all()
        return context
    
    def form_valid(self, form):
        role_matrix = get_object_or_404(RoleMatrix, pk=self.kwargs['pk'])
        
        # Get the skill from cleaned_data (created in form.clean())
        skill = form.cleaned_data.get('skill')
        
        form.instance.role_matrix = role_matrix
        if skill:
            form.instance.skill = skill
        
        return super().form_valid(form)
    
    def form_valid(self, form):
        designation = get_object_or_404(RoleMatrix, pk=self.kwargs['pk'])
        skill = form.cleaned_data.get('skill')
        if skill:
            form.instance.skill = skill
        form.instance.role_matrix = designation
        return super().form_valid(form)


class RoleMatrixBenchmarkDeleteView(SuccessMessageMixin, DeleteView):
    model = SkillBenchmark
    template_name = 'gap_analysis/benchmark_confirm_delete.html'
    success_message = "Benchmark removed successfully!"
    
    def get_success_url(self):
        return reverse('designation_benchmark', kwargs={'pk': self.object.role_matrix.pk})