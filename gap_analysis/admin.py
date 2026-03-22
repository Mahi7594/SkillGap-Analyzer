from django.contrib import admin
from .models import RoleMatrix, SkillBenchmark, SkillMatrix, EmployeeSkill, Skill, EmployeeSkillHistory

@admin.register(RoleMatrix)
class RoleMatrixAdmin(admin.ModelAdmin):
    list_display = ('title', 'department')
    search_fields = ('title', 'department')

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name', 'category')
    list_filter = ('category',)

@admin.register(SkillBenchmark)
class SkillBenchmarkAdmin(admin.ModelAdmin):
    list_display = ('role_matrix', 'skill', 'required_level')
    list_filter = ('role_matrix', 'skill')

@admin.register(SkillMatrix)
class SkillMatrixAdmin(admin.ModelAdmin):
    list_display = ('name', 'role_matrix', 'status')
    list_filter = ('status', 'role_matrix')
    search_fields = ('name',)

@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ('skill_matrix', 'skill', 'actual_level', 'last_evaluated')
    list_filter = ('skill', 'skill_matrix')

@admin.register(EmployeeSkillHistory)
class EmployeeSkillHistoryAdmin(admin.ModelAdmin):
    list_display = ('skill_matrix', 'skill', 'recorded_level', 'evaluated_on')
    list_filter = ('skill', 'evaluated_on')
    readonly_fields = ('evaluated_on',)