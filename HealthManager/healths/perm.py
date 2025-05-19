from rest_framework import permissions
from .models import UserRole, TrackingMode

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.ADMIN

class IsConnectedRegularUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'tracking_mode')
            and request.user.tracking_mode == TrackingMode.CONNECTED
        )

class IsExpert(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [UserRole.TRAINER, UserRole.NUTRITIONIST]

class IsRegularUserWithConnectedTrackingMode(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == UserRole.USER and
            getattr(request.user, 'tracking_mode', None) == TrackingMode.CONNECT_EXPERT
        )


class CanReviewExpert(permissions.BasePermission):
    """
    Chỉ cho phép người dùng đã kết nối với chuyên gia (trainer hoặc nutritionist) được đánh giá họ.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated or user.role != UserRole.USER:
            return False
        return True  # Cho phép kiểm tra tiếp ở `has_object_permission`

    def has_object_permission(self, request, view, obj):
        """
        Kiểm tra user có được phép đánh giá chuyên gia `obj` không.
        `obj` là một instance của Expert.
        """
        user = request.user

        # Kiểm tra kết nối với huấn luyện viên
        if obj.expert_type == UserRole.TRAINER:
            return getattr(user, 'connected_trainer_id', None) == obj.id

        # Kiểm tra kết nối với chuyên gia dinh dưỡng
        if obj.expert_type == UserRole.NUTRITIONIST:
            return getattr(user, 'connected_nutritionist_id', None) == obj.id

        return False

class IsExpertWithProfile(permissions.BasePermission):
    """
    Cho phép truy cập nếu user có role là 'expert' và có expert_profile.
    """
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated
            and user.role == 'expert'
            and hasattr(user, 'expert_profile')
        )