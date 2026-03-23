from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

class RoleMatrix(models.Model):
    title = models.CharField(max_length=100, help_text="Role/Job Title")
    department = models.CharField(max_length=100, blank=True, null=True, help_text="Department name")
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Role Matrices"
        ordering = ['title']
    
    def __str__(self):
        return self.title
    
    @property
    def name(self):
        return self.title
    
    def get_required_skills(self):
        return self.benchmarks.select_related('skill').all()
    
    def get_benchmark_count(self):
        return self.benchmarks.count()

class Skill(models.Model):
    CATEGORY_CHOICES = [
        ('technical', 'Technical'),
        ('soft', 'Soft Skills'),
        ('leadership', 'Leadership'),
        ('domain', 'Domain Knowledge'),
        ('tools', 'Tools & Software'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class SkillBenchmark(models.Model):
    role_matrix = models.ForeignKey(RoleMatrix, on_delete=models.CASCADE, related_name='benchmarks')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='benchmarks')
    required_level = models.IntegerField(
        default=3,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    is_mandatory = models.BooleanField(default=True, help_text="Is this skill mandatory for the role?")
    
    class Meta:
        unique_together = ('role_matrix', 'skill')
        ordering = ['skill__name']
    
    def __str__(self):
        return f"{self.role_matrix.title} - {self.skill.name} (Level {self.required_level})"


class SkillMatrix(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')
    role_matrix = models.ForeignKey(RoleMatrix, on_delete=models.SET_NULL, null=True, blank=True, help_text="Assigned Role")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    join_date = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    def get_skill_count(self):
        return self.skills.count()
    
    def get_assessed_skills(self):
        return self.skills.select_related('skill').all()
    
    def get_required_benchmarks(self):
        if self.role_matrix:
            return self.role_matrix.benchmarks.select_related('skill').all()
        return []
    
    def has_benchmarks(self):
        return self.role_matrix and self.role_matrix.benchmarks.exists()
    
    def get_missing_benchmarks(self):
        if not self.role_matrix:
            return []
        required_skills = set(b.skill.id for b in self.role_matrix.benchmarks.all())
        recorded_skills = set(s.skill.id for s in self.skills.all())
        missing = required_skills - recorded_skills
        return Skill.objects.filter(id__in=missing)
    
    def get_skill_gap_data(self):
        gaps = []
        benchmarks = self.get_required_benchmarks()
        
        if not benchmarks:
            return []
        
        for benchmark in benchmarks:
            emp_skill = self.skills.filter(skill=benchmark.skill).first()
            actual_level = emp_skill.actual_level if emp_skill else 0
            gap = benchmark.required_level - actual_level
            
            gaps.append({
                'skill': benchmark.skill,
                'required_level': benchmark.required_level,
                'actual_level': actual_level,
                'gap': gap,
                'status': 'met' if gap <= 0 else ('warning' if gap <= 1 else 'critical'),
                'emp_skill': emp_skill,
            })
        
        return gaps
    
    def get_overall_gap_score(self):
        gaps = self.get_skill_gap_data()
        if not gaps:
            return 0
        return sum(g['gap'] for g in gaps) / len(gaps)
    
    def get_skills_met_percentage(self):
        gaps = self.get_skill_gap_data()
        if not gaps:
            return 0
        met = sum(1 for g in gaps if g['gap'] <= 0)
        return round((met / len(gaps)) * 100)

class EmployeeSkill(models.Model):
    skill_matrix = models.ForeignKey(SkillMatrix, on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='employee_skills')
    actual_level = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    notes = models.TextField(blank=True, null=True)
    last_evaluated = models.DateField(auto_now=True)
    
    class Meta:
        unique_together = ('skill_matrix', 'skill')
        ordering = ['skill__name']
    
    def __str__(self):
        return f"{self.skill_matrix.name} - {self.skill.name}: {self.actual_level}"
    
    @property
    def employee(self):
        return self.skill_matrix
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_level = None if is_new else EmployeeSkill.objects.get(pk=self.pk).actual_level
        
        super().save(*args, **kwargs)
        
        if not is_new and old_level != self.actual_level:
            EmployeeSkillHistory.objects.create(
                skill_matrix=self.skill_matrix,
                skill=self.skill,
                recorded_level=self.actual_level,
            )

class EmployeeSkillHistory(models.Model):
    skill_matrix = models.ForeignKey(SkillMatrix, on_delete=models.CASCADE, related_name='skill_history')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    recorded_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    evaluated_on = models.DateTimeField(auto_now_add=True)
    evaluated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    @property
    def employee(self):
        return self.skill_matrix
    
    class Meta:
        ordering = ['-evaluated_on']
    
    def __str__(self):
        return f"{self.employee.name} - {self.skill.name}: {self.recorded_level} on {self.evaluated_on}"
