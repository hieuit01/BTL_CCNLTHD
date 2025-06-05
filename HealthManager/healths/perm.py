from rest_framework import permissions
from .models import UserRole, TrackingMode, ExpertType


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

        if not hasattr(user, 'regular_profile'):
            return False
        regular_profile = user.regular_profile

        if obj.expert_type == UserRole.TRAINER:
            return regular_profile.connected_trainer and regular_profile.connected_trainer.id == obj.id

        if obj.expert_type == UserRole.NUTRITIONIST:
            return regular_profile.connected_nutritionist and regular_profile.connected_nutritionist.id == obj.id

        return False


class IsTrainer(permissions.BasePermission):
    def has_permission(self, request, view):
        expert_profile = getattr(request.user, 'expert_profile', None)
        return expert_profile and expert_profile.expert_type == ExpertType.TRAINER


class IsNutritionist(permissions.BasePermission):
    def has_permission(self, request, view):
        expert_profile = getattr(request.user, 'expert_profile', None)
        return expert_profile and expert_profile.expert_type == ExpertType.NUTRITIONIST

class IsRegularUserConnectedMode(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated or request.user.role != UserRole.USER:
            return False
        regular_profile = getattr(request.user, 'regular_profile', None)
        return regular_profile and regular_profile.tracking_mode == TrackingMode.CONNECTED

class IsRegularUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.USER


class IsExpert(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.EXPERT

class IsOwnerOrExpertConnected(permissions.BasePermission):
    """
    Cho phép user thao tác với dữ liệu của chính mình,
    hoặc expert chỉ được xem dữ liệu của user đã kết nối với họ.
    Expert không được tạo/sửa/xóa.
    """

    def has_permission(self, request, view):
        # Phải đăng nhập
        if not request.user.is_authenticated:
            return False

        # Các method không tạo sửa xóa thì expert có thể xem
        if request.method in permissions.SAFE_METHODS:
            return True

        # Các method tạo sửa xóa thì chỉ user thường được làm
        return request.user.role == 'user'

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == 'user':
            # user chỉ thao tác trên dữ liệu của chính mình
            return obj.user.user == user
        elif user.role == 'expert':
            # expert chỉ xem được (SAFE_METHODS) nếu user đó đang kết nối với expert
            if request.method not in permissions.SAFE_METHODS:
                return False

            regular_user = obj.user  # HealthProfile/Tracking.user là RegularUser instance

            # Kiểm tra regular_user có kết nối với expert này không
            connected_trainers = [regular_user.connected_trainer.user] if regular_user.connected_trainer else []
            connected_nutritionists = [regular_user.connected_nutritionist.user] if regular_user.connected_nutritionist else []
            connected_experts = connected_trainers + connected_nutritionists

            return user in connected_experts
        else:
            return False