from ckeditor.widgets import CKEditorWidget
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms

from .models import (
    User, Expert, RegularUser, Review,
    HealthProfile, HealthTracking,
    Workout, WorkoutPlan, WorkoutSession,
    Meal, MealPlan, MealPlanMeal,
    HealthJournal, Reminder, ChatMessage
)


#Các AdminForm
class ExpertAdminForm(forms.ModelForm):
    bio = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Expert
        fields = '__all__'


class WorkoutAdminForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Workout
        fields = '__all__'


class MealAdminForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Meal
        fields = '__all__'


class ReviewAdminForm(forms.ModelForm):
    comment = forms.CharField(widget=CKEditorWidget(), required=False)
    class Meta:
        model = Review
        fields = '__all__'

class MealPlanAdminForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = MealPlan
        fields = '__all__'


class HealthJournalAdminForm(forms.ModelForm):
    note = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = HealthJournal
        fields = '__all__'


class ReminderAdminForm(forms.ModelForm):
    message = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Reminder
        fields = '__all__'

# Tuỳ chỉnh giao diện User (bao gồm cả Expert và RegularUser)
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Thông tin bổ sung', {
            'fields': ('avatar', 'gender', 'phone', 'role')
        }),
    )
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'gender', 'is_active')


@admin.register(Expert)
class ExpertAdmin(admin.ModelAdmin):
    form = ExpertAdminForm
    list_display = ('username', 'expert_type', 'specialization', 'experience_years')
    search_fields = ('username', 'specialization')
    list_filter = ('expert_type',)


@admin.register(RegularUser)
class RegularUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'tracking_mode')
    list_filter = ('tracking_mode',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'expert', 'rating', 'created_at')
    search_fields = ('reviewer__username', 'expert__username')
    list_filter = ('rating',)


@admin.register(HealthProfile)
class HealthProfileAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'height', 'weight', 'age', 'goal')
    list_filter = ('goal',)
    search_fields = ('user_profile__username',)


@admin.register(HealthTracking)
class HealthTrackingAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'date', 'bmi', 'steps', 'heart_rate', 'water_intake')
    list_filter = ('date',)
    search_fields = ('user_profile__username',)

@admin.register(WorkoutPlan)
class WorkoutPlanAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'plan_name', 'start_date', 'end_date', 'status')
    list_filter = ('status',)

@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    form = WorkoutAdminForm
    list_display = ('name', 'duration', 'calories_burned', 'goal')
    search_fields = ('name',)
    list_filter = ('goal',)

@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ('workout_plan', 'workout', 'date', 'status')
    list_filter = ('status', 'date')


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    form = MealAdminForm
    list_display = ('name', 'calories', 'protein', 'carbs', 'fat', 'goal')
    search_fields = ('name',)
    list_filter = ('goal',)


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'plan_name', 'start_date', 'end_date', 'goal')
    list_filter = ('goal',)


@admin.register(MealPlanMeal)
class MealPlanMealAdmin(admin.ModelAdmin):
    list_display = ('meal_plan', 'meal', 'date', 'meal_time')
    list_filter = ('meal_time', 'date')


@admin.register(HealthJournal)
class HealthJournalAdmin(admin.ModelAdmin):
    form = HealthJournalAdminForm
    list_display = ('user_profile', 'date', 'mood')
    list_filter = ('mood', 'date')
    search_fields = ('user_profile__username',)


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    form = ReviewAdminForm
    list_display = ('user_profile', 'reminder_type', 'message', 'send_at')
    list_filter = ('reminder_type', 'send_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'message_type', 'is_read', 'created_date')
    list_filter = ('message_type', 'is_read')
    search_fields = ('sender__username', 'receiver__username')



