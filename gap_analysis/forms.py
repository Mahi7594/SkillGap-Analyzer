from django import forms
from .models import Designation, SkillBenchmark, Employee, EmployeeSkill

class DesignationForm(forms.ModelForm):
    class Meta:
        model = Designation
        fields = '__all__'

class SkillBenchmarkForm(forms.ModelForm):
    class Meta:
        model = SkillBenchmark
        fields = '__all__'

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'

class EmployeeSkillForm(forms.ModelForm):
    class Meta:
        model = EmployeeSkill
        fields = '__all__'