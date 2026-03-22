from django.contrib import admin
from .models import Designation, SkillBenchmark, Employee, EmployeeSkill, Skill

admin.site.register(Designation)
admin.site.register(SkillBenchmark)
admin.site.register(Employee)
admin.site.register(EmployeeSkill)
admin.site.register(Skill)