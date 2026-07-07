from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    RoleMatrix, Skill, SkillBenchmark, SkillMatrix, EmployeeSkill, EmployeeSkillHistory,
    DevelopmentPlan,
)


class GapScoringTests(TestCase):
    def setUp(self):
        self.role = RoleMatrix.objects.create(title='Engineer')
        self.mandatory_skill = Skill.objects.create(name='Python')
        self.mandatory_skill_2 = Skill.objects.create(name='SQL')
        self.optional_skill = Skill.objects.create(name='Public Speaking')

        SkillBenchmark.objects.create(role_matrix=self.role, skill=self.mandatory_skill, required_level=4, is_mandatory=True)
        SkillBenchmark.objects.create(role_matrix=self.role, skill=self.mandatory_skill_2, required_level=3, is_mandatory=True)
        SkillBenchmark.objects.create(role_matrix=self.role, skill=self.optional_skill, required_level=3, is_mandatory=False)

        self.employee = SkillMatrix.objects.create(name='Ada Lovelace', role_matrix=self.role)
        EmployeeSkill.objects.create(skill_matrix=self.employee, skill=self.mandatory_skill, actual_level=1)  # gap 3, mandatory
        EmployeeSkill.objects.create(skill_matrix=self.employee, skill=self.mandatory_skill_2, actual_level=3)  # gap 0, mandatory
        EmployeeSkill.objects.create(skill_matrix=self.employee, skill=self.optional_skill, actual_level=0)  # gap 3, optional

    def test_get_skill_gap_data_computes_gap_and_weight(self):
        gaps = {g['skill'].name: g for g in self.employee.get_skill_gap_data()}
        self.assertEqual(gaps['Python']['gap'], 3)
        self.assertEqual(gaps['Python']['weight'], 2)
        self.assertEqual(gaps['Public Speaking']['gap'], 3)
        self.assertEqual(gaps['Public Speaking']['weight'], 1)

    def test_overall_gap_score_weights_mandatory_skills_higher(self):
        # weighted gaps: Python 3*2=6, SQL 0*2=0, Public Speaking 3*1=3; total weight 2+2+1=5
        self.assertAlmostEqual(self.employee.get_overall_gap_score(), 9 / 5)

    def test_skills_met_percentage_is_unweighted(self):
        # 1 of 3 skills met (SQL)
        self.assertEqual(self.employee.get_skills_met_percentage(), round(1 / 3 * 100))

    def test_no_benchmarks_returns_zero(self):
        lone_employee = SkillMatrix.objects.create(name='No Role')
        self.assertEqual(lone_employee.get_overall_gap_score(), 0)
        self.assertEqual(lone_employee.get_skills_met_percentage(), 0)


class SkillHistoryTests(TestCase):
    def setUp(self):
        self.employee = SkillMatrix.objects.create(name='Ada Lovelace')
        self.python = Skill.objects.create(name='Python')
        self.sql = Skill.objects.create(name='SQL')

    def _change_level(self, skill, new_level):
        """Create-then-update so EmployeeSkill.save() creates a history row (skips on create)."""
        es, _ = EmployeeSkill.objects.get_or_create(skill_matrix=self.employee, skill=skill, defaults={'actual_level': 0})
        es.actual_level = new_level
        es.save()
        return es

    def test_skill_with_multiple_changes_returns_ordered_points(self):
        self._change_level(self.python, 3)  # history row: level 3
        es = self._change_level(self.python, 4)  # history row: level 4

        rows = list(EmployeeSkillHistory.objects.filter(skill_matrix=self.employee, skill=self.python).order_by('pk'))
        EmployeeSkillHistory.objects.filter(pk=rows[0].pk).update(evaluated_on='2026-01-10T00:00:00Z')
        EmployeeSkillHistory.objects.filter(pk=rows[1].pk).update(evaluated_on='2026-01-20T00:00:00Z')
        # Current row's last_evaluated coincides with the latest history point, so it collapses
        # into it rather than adding a synthetic third point.
        EmployeeSkill.objects.filter(pk=es.pk).update(last_evaluated=date(2026, 1, 20))

        history = self.employee.get_skill_history()
        self.assertEqual(history['Python'], [
            {'date': '2026-01-10', 'level': 3},
            {'date': '2026-01-20', 'level': 4},
        ])

    def test_skill_with_no_history_rows_still_returns_current_level(self):
        EmployeeSkill.objects.create(skill_matrix=self.employee, skill=self.sql, actual_level=2)
        EmployeeSkill.objects.filter(skill_matrix=self.employee, skill=self.sql).update(last_evaluated=date(2026, 3, 1))

        history = self.employee.get_skill_history()
        self.assertEqual(history['SQL'], [{'date': '2026-03-01', 'level': 2}])

    def test_same_day_history_points_are_deduped_keeping_the_latest(self):
        EmployeeSkillHistory.objects.create(skill_matrix=self.employee, skill=self.python, recorded_level=3)
        EmployeeSkillHistory.objects.create(skill_matrix=self.employee, skill=self.python, recorded_level=4)
        rows = list(EmployeeSkillHistory.objects.filter(skill_matrix=self.employee, skill=self.python).order_by('pk'))
        for row in rows:
            EmployeeSkillHistory.objects.filter(pk=row.pk).update(evaluated_on='2026-01-10T00:00:00Z')
        # No EmployeeSkill row at all for this skill, so only the two history rows are in play.

        history = self.employee.get_skill_history()
        self.assertEqual(history['Python'], [{'date': '2026-01-10', 'level': 4}])


class ViewAccessControlTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user('hr_admin', password='pass12345', is_staff=True)
        self.plain_user = User.objects.create_user('manager', password='pass12345')
        self.role = RoleMatrix.objects.create(title='Engineer')
        self.employee = SkillMatrix.objects.create(name='Ada Lovelace', role_matrix=self.role)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

        response = self.client.get(reverse('employee_list'))
        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_can_view_dashboard(self):
        self.client.force_login(self.plain_user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_forbidden_from_delete_view(self):
        self.client.force_login(self.plain_user)
        response = self.client.get(reverse('employee_delete', args=[self.employee.id]))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_access_delete_view(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('employee_delete', args=[self.employee.id]))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_forbidden_from_skill_update_endpoint(self):
        self.client.force_login(self.plain_user)
        response = self.client.post(reverse('employee_skill_update', args=[self.employee.id]), {})
        self.assertEqual(response.status_code, 403)


class DevelopmentPlanModelTests(TestCase):
    def setUp(self):
        self.employee = SkillMatrix.objects.create(name='Ada Lovelace')
        self.skill = Skill.objects.create(name='Python')

    def _plan(self, **overrides):
        defaults = {'skill_matrix': self.employee, 'skill': self.skill, 'action': 'Take a course'}
        defaults.update(overrides)
        return DevelopmentPlan.objects.create(**defaults)

    def test_is_overdue_true_for_past_target_date_still_open(self):
        plan = self._plan(target_date=timezone.now().date() - timedelta(days=1), status='in_progress')
        self.assertTrue(plan.is_overdue)

    def test_is_overdue_false_for_future_target_date(self):
        plan = self._plan(target_date=timezone.now().date() + timedelta(days=1), status='in_progress')
        self.assertFalse(plan.is_overdue)

    def test_is_overdue_false_when_completed_even_if_past_due(self):
        plan = self._plan(target_date=timezone.now().date() - timedelta(days=1), status='completed')
        self.assertFalse(plan.is_overdue)

    def test_is_overdue_false_without_target_date(self):
        plan = self._plan(target_date=None, status='in_progress')
        self.assertFalse(plan.is_overdue)


class DevelopmentPlanAccessControlTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user('hr_admin', password='pass12345', is_staff=True)
        self.plain_user = User.objects.create_user('manager', password='pass12345')
        self.role = RoleMatrix.objects.create(title='Engineer')
        self.skill = Skill.objects.create(name='Python')
        SkillBenchmark.objects.create(role_matrix=self.role, skill=self.skill, required_level=4)
        self.employee = SkillMatrix.objects.create(name='Ada Lovelace', role_matrix=self.role)
        self.plan = DevelopmentPlan.objects.create(
            skill_matrix=self.employee, skill=self.skill, action='Take a course',
        )

    def test_plain_user_can_view_plan_list_and_profile_plans_tab(self):
        self.client.force_login(self.plain_user)
        self.assertEqual(self.client.get(reverse('development_plan_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('employee_profile', args=[self.employee.id])).status_code, 200)

    def test_non_staff_forbidden_from_creating_a_plan(self):
        self.client.force_login(self.plain_user)
        response = self.client.get(reverse('development_plan_add', args=[self.employee.id]))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_update_and_delete_a_plan(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(reverse('development_plan_add', args=[self.employee.id]), {
            'skill': self.skill.id,
            'action': 'Pair with a senior dev',
            'status': 'not_started',
        })
        self.assertEqual(response.status_code, 302)
        new_plan = DevelopmentPlan.objects.get(action='Pair with a senior dev')
        self.assertEqual(new_plan.created_by, self.staff_user)

        response = self.client.post(reverse('development_plan_update', args=[new_plan.id]), {
            'skill': self.skill.id,
            'action': 'Pair with a senior dev',
            'status': 'in_progress',
        })
        self.assertEqual(response.status_code, 302)
        new_plan.refresh_from_db()
        self.assertEqual(new_plan.status, 'in_progress')

        response = self.client.post(reverse('development_plan_delete', args=[new_plan.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(DevelopmentPlan.objects.filter(id=new_plan.id).exists())
