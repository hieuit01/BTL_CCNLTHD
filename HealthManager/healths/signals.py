# Trong healths/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import WorkoutSession, WorkoutPlan, SessionStatus, PlanStatus

@receiver(post_save, sender=WorkoutSession)
@receiver(post_delete, sender=WorkoutSession)
def update_workout_plan_status(sender, instance, **kwargs):
    """
    Signal được gọi sau khi lưu hoặc xóa một WorkoutSession.
    Nó sẽ kiểm tra trạng thái của tất cả các WorkoutSession
    và cập nhật status trong WorkoutPlan.
    """
    workout_plan = instance.workout_plan  # Lấy WorkoutPlan liên kết

    # Lấy tất cả các WorkoutSession của WorkoutPlan và kiểm tra trạng thái của chúng
    sessions = workout_plan.sessions.all()
    all_completed = all(session.status == SessionStatus.COMPLETED for session in sessions)
    any_pending = any(session.status == SessionStatus.PENDING for session in sessions)

    # Cập nhật trạng thái của WorkoutPlan
    if any_pending:
        workout_plan.status = PlanStatus.PENDING  # Nếu có ít nhất 1 bài tập đang pending
    elif all_completed:
        workout_plan.status = PlanStatus.COMPLETED  # Nếu tất cả bài tập đều completed
    else:
        workout_plan.status = PlanStatus.PENDING  # Mặc định nếu có sự thay đổi nào

    workout_plan.save()  # Lưu lại trạng thái mới cho WorkoutPlan
