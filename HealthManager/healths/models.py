from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField

class User(AbstractUser):
    # Định nghĩa các lựa chọn cho vai trò người dùng
    ROLE_CHOICES = (
        ('user', 'Người dùng'),  # 'user' là giá trị lưu trong database, 'Người dùng' là giá trị hiển thị
        ('expert', 'Chuyên gia'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="user")
    avatar = CloudinaryField(null=True)

class OAuth2Provider(models.Model):
    provider_name = models.CharField(max_length=255)
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    redirect_uri = models.CharField(max_length=255)

class UserSocialLogin(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.ForeignKey(OAuth2Provider, on_delete=models.CASCADE)
    social_id = models.CharField(max_length=255)
    access_token = models.CharField(max_length=1024)
    refresh_token = models.CharField(max_length=1024, blank=True, null=True)
    expires_at = models.DateTimeField()

class ExpertProfile(models.Model):
    expert = models.OneToOneField(User, on_delete=models.CASCADE, related_name='expert_profile')
    specialization = models.CharField(max_length=255)
    experience_years = models.IntegerField()
    bio = models.TextField()

class UserProfile(models.Model):
    TRACKING_MODE_CHOICES = [
        ('personal', 'Theo dõi cá nhân'),
        ('connected', 'Kết nối với chuyên gia'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tracking_mode = models.CharField(max_length=20, choices=TRACKING_MODE_CHOICES)
    connected_expert = models.ForeignKey(ExpertProfile, on_delete=models.SET_NULL, null=True, blank=True)

# Hồ sơ sức khỏe
class HealthProfile(models.Model):
    # Định nghĩa các lựa chọn cho mục tiêu sức khỏe
    GOAL_CHOICES = (
        ('gain_muscle', 'Tăng cơ'),  # 'gain_muscle' là giá trị lưu trong database, 'Tăng cơ' là giá trị hiển thị
        ('lose_weight', 'Giảm cân'),
        ('maintain', 'Duy trì sức khỏe'),
    )
    # Trường khóa ngoại một-một liên kết với mô hình UserProfile
    # on_delete=models.CASCADE: Nếu UserProfile bị xóa, HealthProfile tương ứng cũng bị xóa
    # related_name="health_profile": Cho phép truy cập HealthProfile từ User qua user.health_profile
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="health_profile")
    # Trường lưu trữ chiều cao (đơn vị cm)
    height = models.FloatField(help_text="Chiều cao (cm)")
    # Trường lưu trữ cân nặng (đơn vị kg)
    weight = models.FloatField(help_text="Cân nặng (kg)")
    # Trường lưu trữ tuổi
    age = models.IntegerField()
    # Trường lưu trữ mục tiêu sức khỏe, mặc định là 'maintain'
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES, default='maintain')
    # Phương thức tính toán chỉ số BMI
    def calculate_bmi(self):
        return self.weight / ((self.height / 100) ** 2)

    # Phương thức trả về chuỗi đại diện cho đối tượng HealthProfile
    def __str__(self):
        return f"Hồ sơ sức khỏe của {self.user.username}"

# Theo dõi sức khỏe hàng ngày
class HealthTracking(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="health_tracking")
    date = models.DateField(auto_now_add=True)
    bmi = models.FloatField(null=True, blank=True)  # Lưu BMI mỗi ngày
    steps = models.IntegerField(default=0)
    heart_rate = models.IntegerField(null=True, blank=True)  # Nhịp tim (nếu có thiết bị đo)
    water_intake = models.FloatField(default=0.0, help_text="Lượng nước uống (lít)")

    def save(self, *args, **kwargs):
        if not self.bmi and hasattr(self.user, 'health_profile'):
            self.bmi = self.user.health_profile.calculate_bmi()  # Lấy BMI từ HealthProfile
        super().save(*args, **kwargs)

# Kế hoạch luyện tập
class WorkoutPlan(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="workout_schedules")
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=[("pending", "Chưa thực hiện"), ("completed", "Hoàn thành")], default="pending")

# Bài tập
class Workout(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    duration = models.IntegerField(help_text="Thời gian tập luyện (phút)")
    calories_burned = models.IntegerField(help_text="Lượng calo tiêu thụ")
    difficulty = models.CharField(max_length=50, choices=[("easy", "Dễ"), ("medium", "Trung bình"), ("hard", "Khó")])
    plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE)

class WorkoutPlan_Workout(models.Model):
    DayOfWeek = [
        ('MONDAY', 'Thứ hai'),
        ('TUESDAY', 'Thứ ba'),
        ('WEDNESDAY', 'Thứ tư'),
        ('THURSDAY', 'Thứ năm'),
        ('FRIDAY', 'Thứ sáu'),
        ('SATURDAY', 'Thứ bảy'),
        ('SUNDAY', 'sChủ nhật'),
    ]

    workout_plan_workout_id = models.AutoField(primary_key=True)
    plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE)
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE)
    day_of_week = models.CharField(max_length=20, choices=DayOfWeek)
    sets = models.IntegerField()
    reps = models.IntegerField()
    duration = models.IntegerField(help_text="Duration in minutes")
    notes = models.TextField()

# Thực ơn dinh dưỡng
class MealPlan(models.Model):
    GOAL_CHOICES = (
        ('gain_muscle', 'Tăng cơ'),  # 'gain_muscle' là giá trị lưu trong database, 'Tăng cơ' là giá trị hiển thị
        ('lose_weight', 'Giảm cân'),
        ('maintain', 'Duy trì sức khỏe'),
    )

    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="meal_plans")
    health_profile = models.ForeignKey(HealthProfile, on_delete=models.CASCADE)
    plan_name = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# Món ăn
class Meal(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    calories = models.IntegerField(help_text="Lượng calo (kcal)")
    protein = models.FloatField(help_text="Lượng protein (g)")
    carbs = models.FloatField(help_text="Lượng carbohydrate (g)")
    fat = models.FloatField(help_text="Lượng chất béo (g)")
    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE)

class MealPlan_Meal(models.Model):
    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE)
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    meal_type = models.CharField(max_length=20, choices=[("breakfast", "Bữa sáng"), ("lunch", "Bữa trưa"), ("dinner", "Bữa tối")])
    serving_size = models.CharField(max_length=255)
    notes = models.TextField()

# Nhật ký sức khỏe
class HealthJournal(models.Model):
    MOOD_CHOICES = (
        ("happy", "Vui"),
        ("normal", "Bình thường"),
        ("tired", "Mệt mỏi"),
        ("stressed", "Căng thẳng"),
    )

    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="health_journals")
    date = models.DateField(auto_now_add=True)
    note = models.TextField()
    mood = models.CharField(max_length=50, choices=MOOD_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.date}"

# Nhắc nhở
class Reminder(models.Model):
    REMINDER_TYPE_CHOICES = (
        ("water", "Uống nước"),
        ("workout", "Tập luyện"),
        ("rest", "Nghỉ ngơi"),
    )

    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="reminders")
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    message = models.CharField(max_length=255)
    time = models.TimeField()

    def __str__(self):
        return f"{self.user.username} - {self.get_reminder_type_display()} lúc {self.time}"



# Chat trực tiếp (nâng cao)
class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} lúc {self.timestamp}"
