from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.db.models import Avg, Sum
from datetime import  date
from django import forms
from django.utils.html import mark_safe
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.db.models.functions import TruncWeek, TruncMonth
from django.core.exceptions import PermissionDenied

from .models import (
    User, RegularUser, Expert, Review,
    HealthProfile, HealthTracking,
    Workout, WorkoutPlan, WorkoutSession,
    Meal, MealPlan, MealPlanMeal,
    HealthJournal, Reminder,
    ChatMessage, TrackingMode, ExpertType
)

# ----- User Admin -----
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'role', 'gender', 'phone', 'email', 'is_active']
    list_filter = ['id', 'role', 'gender', 'is_active']
    search_fields = ['username', 'email', 'phone']
    readonly_fields = ['avatar_view']

    def avatar_view(self, user):
        if user.avatar:
            return mark_safe(f"<img src='{user.avatar.url}' width=200 />")
        return "Không có ảnh đại diện"

    avatar_view.short_description = "Ảnh đại diện"

    def save_model(self, request, user, form, change):
        raw_password = form.cleaned_data.get('password')
        if raw_password and not raw_password.startswith('pbkdf2_'):
            user.set_password(raw_password)
        super().save_model(request, user, form, change)


# ----- RegularUser Admin -----
class RegularUserAdminForm(forms.ModelForm):
    class Meta:
        model = RegularUser
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        tracking_mode = cleaned_data.get('tracking_mode')
        trainer = cleaned_data.get('connected_trainer')
        nutritionist = cleaned_data.get('connected_nutritionist')

        if tracking_mode == TrackingMode.PERSONAL and (trainer or nutritionist):
            raise forms.ValidationError("Chế độ cá nhân không được liên kết với chuyên gia.")
        return cleaned_data

class RegularUserAdmin(admin.ModelAdmin):
    form = RegularUserAdminForm
    list_display = [
        'id', 'get_username', 'get_full_name', 'tracking_mode',
        'get_trainer_id', 'get_trainer_username',
        'get_nutritionist_id', 'get_nutritionist_username',
        'active', 'created_date',
    ]
    list_filter = ['id', 'tracking_mode', 'active']
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'connected_trainer__user__username', 'connected_nutritionist__user__username'
    ]

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(role='user')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description='Username')
    def get_username(self, obj):
        return obj.user.username

    @admin.display(description='Fullname')
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or "(Chưa có tên)"

    @admin.display(description='ID trainer')
    def get_trainer_id(self, obj):
        return obj.connected_trainer.user.id if obj.connected_trainer else "-"

    @admin.display(description='Trainer name')
    def get_trainer_username(self, obj):
        if obj.connected_trainer:
            user = obj.connected_trainer.user
            return user.username
        return "-"

    @admin.display(description='ID Nutritionist')
    def get_nutritionist_id(self, obj):
        return obj.connected_nutritionist.user.id if obj.connected_nutritionist else "-"

    @admin.display(description='Nutritionist name')
    def get_nutritionist_username(self, obj):
        if obj.connected_nutritionist:
            user = obj.connected_nutritionist.user
            return user.username
        return "-"


# ----- Expert Admin -----
class ExpertAdminForm(forms.ModelForm):
    bio = forms.CharField(widget=CKEditorUploadingWidget(), required=False)

    class Meta:
        model = Expert
        fields = '__all__'

class ExpertAdmin(admin.ModelAdmin):
    form = ExpertAdminForm

    list_display = ['id', 'user', 'get_full_name', 'expert_type', 'specialization', 'experience_years', 'active', 'created_date', 'avg_rating']
    list_filter = ['id', 'expert_type', 'active']
    search_fields = ['user__username', 'specialization']

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(role='expert')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def avg_rating(self, obj):
        avg = obj.reviews.aggregate(avg=Avg('rating'))['avg']
        return round(avg, 2) if avg else '-'
    avg_rating.short_description = 'Rating'

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    get_full_name.short_description = 'Full Name'

# ----- Review Admin -----
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'reviewer_id',
        'reviewer_name',
        'expert_id',
        'expert_name',
        'rating',
        'comment',
        'created_at',
    ]

    def reviewer_id(self, obj):
        return obj.reviewer.user.id
    reviewer_id.short_description = 'Reviewer ID'
    reviewer_id.admin_order_field = 'reviewer__user__id'

    def reviewer_name(self, obj):
        return obj.reviewer.user.get_full_name() or obj.reviewer.user.username
    reviewer_name.short_description = 'Reviewer Name'
    reviewer_name.admin_order_field = 'reviewer__user__username'

    def expert_id(self, obj):
        return obj.expert.user.id
    expert_id.short_description = 'Expert ID'
    expert_id.admin_order_field = 'expert__user__id'

    def expert_name(self, obj):
        return obj.expert.user.get_full_name() or obj.expert.user.username
    expert_name.short_description = 'Expert Name'
    expert_name.admin_order_field = 'expert__user__username'


# ----- HealthProfile Admin -----
class HealthProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'height', 'weight', 'age', 'goal', 'created_date']
    list_filter = ['id', 'goal', 'id']
    search_fields = ['user__user__username']

# ----- HealthTracking Admin -----
class HealthTrackingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'date', 'bmi', 'steps', 'heart_rate', 'water_intake']
    list_filter = ['id', 'date']
    search_fields = ['user__user__username']
    date_hierarchy = 'date'

# ----- Workout Admin -----
class WorkoutAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'goal',
        'created_by', 'suggested_to', 'is_public', 'active', 'created_date'
    ]
    list_filter = ['goal', 'is_public', 'active', 'created_date']
    search_fields = ['name']
    readonly_fields = ['image_view']
    autocomplete_fields = ['created_by', 'suggested_to']

    def image_view(self, workout):
        if workout.image:
            return mark_safe(f"<img src='{workout.image.url}' width=200 />")
        return "Không có ảnh"
    image_view.short_description = "Hình ảnh"

    # def get_form(self, request, obj=None, **kwargs):
    #     form = super().get_form(request, obj, **kwargs)
    #
    #     # Nếu là chuyên gia
    #     if request.user.role == 'expert' and hasattr(request.user, 'expert_profile'):
    #         expert = request.user.expert_profile
    #
    #         if expert.expert_type == 'trainer':
    #             # Danh sách user kết nối với chuyên gia dinh dưỡng này
    #             qs = RegularUser.objects.filter(connected_trainer=expert)
    #
    #             # Nếu đang edit và giá trị suggested_to hiện tại không nằm trong danh sách, thêm vào
    #             if obj and obj.suggested_to and obj.suggested_to not in qs:
    #                 qs = RegularUser.objects.filter(pk=obj.suggested_to.pk) | qs
    #
    #             form.base_fields['suggested_to'].queryset = qs
    #         else:
    #             # Không phải chuyên gia dinh dưỡng thì không cho gợi ý
    #             form.base_fields['suggested_to'].queryset = RegularUser.objects.none()
    #
    #     elif request.user.role != 'admin':
    #         # Người dùng thường không được gợi ý
    #         form.base_fields['suggested_to'].queryset = RegularUser.objects.none()
    #
    #     return form
    #
    # def save_model(self, request, obj, form, change):
    #     user = request.user
    #
    #     # Nếu là bài tập gợi ý
    #     if obj.suggested_to:
    #         if user.role != 'expert' or not hasattr(user, 'expert_profile'):
    #             raise PermissionDenied("Chỉ chuyên gia mới được gợi ý bài tập cho người dùng.")
    #
    #         expert = user.expert_profile
    #
    #         if expert.expert_type == ExpertType.TRAINER:
    #             if obj.suggested_to.connected_trainer_id != expert.id:
    #                 raise PermissionDenied("Bạn chỉ được gợi ý bài tập cho người dùng đã kết nối với bạn.")
    #         elif expert.expert_type == ExpertType.NUTRITIONIST:
    #             if obj.suggested_to.connected_nutritionist_id != expert.id:
    #                 raise PermissionDenied("Bạn chỉ được gợi ý bài tập cho người dùng đã kết nối với bạn.")
    #         else:
    #             raise PermissionDenied("Loại chuyên gia không hợp lệ.")
    #
    #     # Gán người tạo nếu là tạo mới
    #     if not obj.pk:
    #         obj.created_by = user
    #
    #     # Luôn set is_public = False nếu không phải admin
    #     if not user.is_superuser:
    #         obj.is_public = False
    #
    #     super().save_model(request, obj, form, change)


# Inline để hiển thị và chỉnh sửa WorkoutSession bên trong WorkoutPlan
class WorkoutSessionInline(admin.TabularInline):
    model = WorkoutSession
    extra = 1
    fields = ['workout', 'date', 'duration', 'status']
    readonly_fields = []
    show_change_link = True

# ----- WorkoutPlan Admin -----
class WorkoutPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'plan_name', 'start_date', 'end_date', 'created_date']
    list_filter = ['start_date', 'end_date', 'created_date']
    search_fields = ['user__user__username', 'plan_name']
    inlines = [WorkoutSessionInline]

# ----- WorkoutSession Admin -----
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'workout_plan', 'workout', 'date', 'duration', 'status']
    list_filter = ['status', 'date']
    search_fields = ['workout_plan__user__user__username', 'workout__name']
    date_hierarchy = 'date'

# ----- Meal Admin -----
class MealAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'goal', 'calories', 'created_by',
        'suggested_to', 'is_public', 'active', 'created_date'
    ]
    list_filter = ['goal', 'is_public', 'active', 'created_date']
    search_fields = ['name']
    readonly_fields = ['image_view']
    autocomplete_fields = ['created_by', 'suggested_to']

    def image_view(self, meal):
        if meal.image:
            return mark_safe(f"<img src='{meal.image.url}' width=200 />")
        return "Không có ảnh"
    image_view.short_description = "Hình ảnh"

    # def get_form(self, request, obj=None, **kwargs):
    #     form = super().get_form(request, obj, **kwargs)
    #
    #     # Nếu là chuyên gia
    #     if request.user.role == 'expert' and hasattr(request.user, 'expert_profile'):
    #         expert = request.user.expert_profile
    #
    #         if expert.expert_type == ExpertType.NUTRITIONIST: # Sử dụng ExpertType.NUTRITIONIST từ enum
    #             # Danh sách user kết nối với chuyên gia dinh dưỡng này
    #             qs = RegularUser.objects.filter(connected_nutritionist=expert)
    #
    #             # Nếu đang edit và giá trị suggested_to hiện tại không nằm trong danh sách, thêm vào
    #             if obj and obj.suggested_to and obj.suggested_to not in qs:
    #                 qs = RegularUser.objects.filter(pk=obj.suggested_to.pk) | qs
    #
    #             form.base_fields['suggested_to'].queryset = qs
    #         else:
    #             # Nếu không phải chuyên gia dinh dưỡng thì không cho gợi ý bữa ăn
    #             form.base_fields['suggested_to'].queryset = RegularUser.objects.none()
    #
    #     elif request.user.role != 'admin':
    #         # Người dùng thường và các vai trò khác không được gợi ý
    #         form.base_fields['suggested_to'].queryset = RegularUser.objects.none()
    #
    #     return form
    #
    # def save_model(self, request, obj, form, change):
    #     user = request.user
    #
    #     if obj.suggested_to:
    #         # Chỉ chuyên gia mới được gợi ý
    #         if user.role != 'expert' or not hasattr(user, 'expert_profile'):
    #             raise PermissionDenied("Bạn không có quyền gợi ý bữa ăn.")
    #
    #         expert = user.expert_profile
    #
    #         # Chỉ chuyên gia dinh dưỡng mới được gợi ý bữa ăn
    #         if expert.expert_type != ExpertType.NUTRITIONIST:
    #             raise PermissionDenied("Chỉ chuyên gia dinh dưỡng mới được gợi ý bữa ăn.")
    #
    #         # Đảm bảo người dùng được gợi ý đã kết nối với chuyên gia dinh dưỡng này
    #         if obj.suggested_to.connected_nutritionist_id != expert.id:
    #             raise PermissionDenied("Bạn chỉ được gợi ý bữa ăn cho người dùng đã kết nối với bạn với tư cách chuyên gia dinh dưỡng.")
    #
    #     if not obj.pk:
    #         obj.created_by = user
    #
    #     # Luôn set is_public = False nếu không phải admin
    #     if not user.is_superuser: # Giữ logic này để chỉ admin mới có thể công khai bữa ăn
    #          obj.is_public = False
    #
    #     super().save_model(request, obj, form, change)

# ----- MealPlan Admin -----
class MealPlanMealInline(admin.TabularInline):
    model = MealPlanMeal
    extra = 1  # số dòng trống thêm mới
    fields = ['meal', 'date', 'meal_time']
    readonly_fields = []
    show_change_link = True
    autocomplete_fields = ['meal']

class MealPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'plan_name', 'user', 'goal', 'start_date', 'end_date', 'active', 'created_date']
    list_filter = ['goal', 'active', 'start_date', 'end_date']
    search_fields = ['plan_name', 'user__user__username']
    inlines = [MealPlanMealInline]
    autocomplete_fields = ['user']

# ----- MealPlanMeal Admin -----
class MealPlanMealAdmin(admin.ModelAdmin):
    list_display = ['id', 'meal_plan', 'meal', 'date', 'meal_time', 'active']
    list_filter = ['meal_time', 'active', 'date']
    search_fields = ['meal_plan__plan_name', 'meal__name']
    date_hierarchy = 'date'
    autocomplete_fields = ['meal_plan', 'meal']

# ----- HealthJournal Admin -----
class HealthJournalAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'date', 'mood', 'note_truncated']
    list_filter = ('id', 'mood', 'date')
    search_fields = ('user__user__username', 'note')

    def note_truncated(self, obj):
        return (obj.note[:75] + '...') if len(obj.note) > 75 else obj.note
    note_truncated.short_description = 'Ghi chú'

# ----- Reminder Admin -----
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('user', 'reminder_type', 'message', 'send_at', 'active')
    list_filter = ('reminder_type', 'active', 'send_at')
    search_fields = ('user__user__username', 'message')
    date_hierarchy = 'send_at'

# ----- ChatMessage Admin -----
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'message_type', 'is_read', 'created_date')
    list_filter = ('message_type', 'is_read', 'created_date')
    search_fields = ('sender__username', 'receiver__username', 'message')
    readonly_fields = ('created_date', 'updated_date')

class ReportFilterForm(forms.Form):
    user_id = forms.IntegerField(required=False, label="ID người dùng")
    year = forms.IntegerField(initial=date.today().year, label="Năm")
    month = forms.IntegerField(required=False, min_value=1, max_value=12, label="Tháng")
    week = forms.IntegerField(required=False, min_value=1, max_value=53, label="Tuần")

class HealthAdminSite(admin.AdminSite):
    site_header = 'Hệ thống Quản Lý Sức Khỏe Và Theo Dõi Hoạt Động Cá Nhân'
    site_title = "Quản trị sức khỏe"
    index_title = "Bảng điều khiển quản trị"

    def get_urls(self):
        return [path('user-progress/', self.user_progress_view)] + super().get_urls()

    def user_progress_view(self, request):
        form = ReportFilterForm(request.GET or None)
        statistics = []

        if form.is_valid():
            user_id = form.cleaned_data.get('user_id')
            year = form.cleaned_data.get('year')
            month = form.cleaned_data.get('month')
            week = form.cleaned_data.get('week')


            qs = HealthTracking.objects.filter(date__year=year)
            if user_id:
                qs = qs.filter(user_id=user_id)

            if week:
                qs = qs.filter(date__week=week, date__year=year).annotate(period=TruncWeek('date'))
            elif month:
                qs = qs.filter(date__month=month).annotate(period=TruncMonth('date'))
            else:
                qs = qs.annotate(period=TruncMonth('date'))

            statistics = qs.values('period').annotate(
                total_steps=Sum('steps'),
                avg_bmi=Avg('bmi'),
                avg_heart_rate=Avg('heart_rate'),
                total_water_intake=Sum('water_intake'),
            ).order_by('period')

        return TemplateResponse(request, 'admin/user_progress.html', {
            'form': form,
            'statistics': statistics,
        })

admin_site = HealthAdminSite(name='myadmin')

admin_site.register(User, UserAdmin)
admin_site.register(RegularUser, RegularUserAdmin)
admin_site.register(Expert, ExpertAdmin)
admin_site.register(Review, ReviewAdmin)
admin_site.register(HealthProfile, HealthProfileAdmin)
admin_site.register(HealthTracking, HealthTrackingAdmin)
admin_site.register(Workout, WorkoutAdmin)
admin_site.register(WorkoutPlan, WorkoutPlanAdmin)
admin_site.register(WorkoutSession, WorkoutSessionAdmin)
admin_site.register(Meal, MealAdmin)
admin_site.register(MealPlan, MealPlanAdmin)
admin_site.register(MealPlanMeal, MealPlanMealAdmin)
admin_site.register(HealthJournal, HealthJournalAdmin)
admin_site.register(Reminder, ReminderAdmin)
admin_site.register(ChatMessage, ChatMessageAdmin)