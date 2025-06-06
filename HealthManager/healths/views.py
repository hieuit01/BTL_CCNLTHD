from rest_framework import viewsets, status, generics, permissions, parsers, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import (User, Expert, Workout, Review, RegularUser, ExpertType, Gender, HealthProfile, HealthTracking,
                     WorkoutPlan, MealPlan, Meal, HealthJournal, Reminder, ChatMessage, WorkoutSession)
from .serializers import (UserSerializer, ReviewSerializer, UserConnectedSerializer, ExpertSerializer, MealSerializer,
                          HealthProfileSerializer, HealthTrackingSerializer, WorkoutSerializer, WorkoutPlanSerializer,
                          MealPlanSerializer, HealthJournalSerializer, ReminderSerializer, ChatMessageSerializer)
from .perm import CanReviewExpert, IsExpert, IsRegularUser, IsOwnerOrExpertConnected, IsTrainer
from django.db.models import Q, Avg, F, Case, When, Value, FloatField, Sum
from django.utils.timezone import now, timedelta


def success_response(message, data, status_code=status.HTTP_200_OK):
    return Response({'message': message, 'data': data}, status=status_code)

def error_response(message, status_code=400):
    return Response({"success": False, "message": message, "data": None}, status=status_code)

# ------UserViewSet------
class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer  # Dùng để đăng ký user thường
    parser_classes = [parsers.MultiPartParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = UserSerializer(user).data  # user đã là instance User rồi
        return success_response("Đăng ký người dùng thành công", data, status.HTTP_201_CREATED)

    @action(methods=['get', 'patch'], url_path='current-user', detail=False,
            permission_classes=[permissions.IsAuthenticated, IsRegularUser])
    def current_user(self, request):
        user = request.user

        allowed_fields = ['first_name', 'last_name', 'email', 'phone', 'gender', 'avatar']

        if request.method == 'PATCH':
            data = request.data
            invalid_fields = []

            for field in data.keys():
                if field not in allowed_fields + ['password']:
                    invalid_fields.append(field)

            if invalid_fields:
                return error_response(
                    {"invalid_fields": invalid_fields},
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            if 'gender' in data:
                if data['gender'] not in [choice.value for choice in Gender]:
                    return error_response(
                        {"gender": "Giá trị giới tính không hợp lệ."},
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

            for field in allowed_fields:
                if field in data:
                    setattr(user, field, data[field])

            if 'password' in data:
                user.set_password(data['password'])

            user.save()

            serializer = UserSerializer(user)
            return success_response("Cập nhật thông tin người dùng thành công", serializer.data)

        # GET method: trả về thông tin user
        serializer = UserSerializer(user)
        return success_response("Lấy thông tin người dùng", serializer.data)

    @action(methods=['get', 'patch'], url_path='tracking', detail=False,
            permission_classes=[permissions.IsAuthenticated, IsRegularUser])
    def tracking(self, request):
        regular = getattr(request.user, 'regular_profile', None)
        if not regular:
            return  error_response({'detail': 'Bạn không phải người dùng thường'}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'PATCH':
            serializer = UserConnectedSerializer(regular, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return success_response("Cập nhật chế độ theo dõi thành công", serializer.data)

        return success_response("Thông tin chế độ theo dõi", UserConnectedSerializer(regular).data)

# ------ExpertViewSet------
class ExpertViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = Expert.objects.all()
    serializer_class = ExpertSerializer
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser]


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expert = serializer.save()
        data = ExpertSerializer(expert).data
        return success_response("Đăng ký chuyên gia thành công", data, status.HTTP_201_CREATED)

    @action(methods=['get', 'patch'], url_path='current-expert', detail=False,
            permission_classes=[permissions.IsAuthenticated, IsExpert])
    def current_expert(self, request):
        expert = request.user.expert_profile
        user = request.user

        allowed_expert_fields = ['specialization', 'experience_years', 'bio']
        allowed_user_fields = ['first_name', 'last_name', 'email', 'phone', 'gender', 'avatar']

        if request.method == 'PATCH':
            data = request.data
            invalid_fields = []

            for field in data.keys():
                if field not in allowed_expert_fields + allowed_user_fields + ['password']:
                    invalid_fields.append(field)

            if invalid_fields:
                return error_response(
                    {"invalid_fields": invalid_fields},
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Kiểm tra gender nếu có
            if 'gender' in data:
                if data['gender'] not in [choice.value for choice in Gender]:
                    return error_response(
                        {"gender": "Giá trị giới tính không hợp lệ."},
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

            # Cập nhật expert fields
            for field in allowed_expert_fields:
                if field in data:
                    setattr(expert, field, data[field])

            # Cập nhật user fields
            for field in allowed_user_fields:
                if field in data:
                    setattr(user, field, data[field])

            # Cập nhật password nếu có
            if 'password' in data:
                user.set_password(data['password'])

            expert.save()
            user.save()

            serializer = ExpertSerializer(expert)
            return success_response("Cập nhật thông tin chuyên gia thành công", serializer.data)

        # GET method: trả về dữ liệu chuyên gia
        serializer = ExpertSerializer(expert)
        return success_response("Lấy thông tin chuyên gia", serializer.data)

    @action(methods=['get'], detail=False, url_path='trainers',
            permission_classes=[permissions.IsAuthenticated, IsRegularUser])
    def list_trainers(self, request):
        queryset = Expert.objects.filter(expert_type=ExpertType.TRAINER).annotate(
            avg_rating=Avg('reviews__rating')
        ).annotate(
            sort_rating=Case(
                When(avg_rating__isnull=True, then=Value(-1)),
                default=F('avg_rating'),
                output_field=FloatField()
            )
        )

        # Lọc theo min_rating nếu có
        min_rating = request.query_params.get('min_rating')
        if min_rating is not None:
            try:
                min_rating = float(min_rating)
                queryset = queryset.filter(avg_rating__gte=min_rating)
            except ValueError:
                pass

        # Lọc theo specialization nếu có
        specialization = request.query_params.get('specialization')
        if specialization:
            queryset = queryset.filter(specialization__icontains=specialization)

        # Lọc theo min_experience nếu có
        min_experience = request.query_params.get('min_experience')
        if min_experience is not None:
            try:
                min_experience = int(min_experience)
                queryset = queryset.filter(experience_years__gte=min_experience)
            except ValueError:
                pass

        queryset = queryset.order_by('-sort_rating', 'user__last_name')

        serializer = ExpertSerializer(queryset, many=True)
        return success_response("Danh sách huấn luyện viên", serializer.data)

    @action(methods=['get'], detail=False, url_path='nutritionists',
            permission_classes=[permissions.IsAuthenticated, IsRegularUser])
    def list_nutritionists(self, request):
        queryset = Expert.objects.filter(expert_type=ExpertType.NUTRITIONIST).annotate(
            avg_rating=Avg('reviews__rating')
        ).annotate(
            sort_rating=Case(
                When(avg_rating__isnull=True, then=Value(-1)),
                default=F('avg_rating'),
                output_field=FloatField()
            )
        )

        min_rating = request.query_params.get('min_rating')
        if min_rating is not None:
            try:
                min_rating = float(min_rating)
                queryset = queryset.filter(avg_rating__gte=min_rating)
            except ValueError:
                pass

        specialization = request.query_params.get('specialization')
        if specialization:
            queryset = queryset.filter(specialization__icontains=specialization)

        min_experience = request.query_params.get('min_experience')
        if min_experience is not None:
            try:
                min_experience = int(min_experience)
                queryset = queryset.filter(experience_years__gte=min_experience)
            except ValueError:
                pass

        queryset = queryset.order_by('-sort_rating', 'user__last_name')

        serializer = ExpertSerializer(queryset, many=True)
        return success_response("Danh sách chuyên gia dinh dưỡng", serializer.data)

    @action(methods=['get'], url_path='connected-users', detail=False,
            permission_classes=[permissions.IsAuthenticated, IsExpert])
    def connected_users(self, request):
        expert = request.user.expert_profile
        users_queryset = User.objects.none()  # Khởi tạo queryset rỗng

        if expert.expert_type == ExpertType.TRAINER:
            # Lọc User dựa trên RegularUser được kết nối với trainer
            users_queryset = User.objects.filter(regular_profile__connected_trainer=expert)
        elif expert.expert_type == ExpertType.NUTRITIONIST:
            # Lọc User dựa trên RegularUser được kết nối với nutritionist
            users_queryset = User.objects.filter(regular_profile__connected_nutritionist=expert)

        # Áp dụng tìm kiếm
        search_query = request.query_params.get('q', None)
        if search_query:
            users_queryset = users_queryset.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )

        users_queryset = users_queryset.order_by('last_name')  # Sắp xếp

        serializer = UserSerializer(users_queryset, many=True)

        return success_response("Danh sách người dùng đang kết nối", serializer.data)

    @action(methods=['get'], url_path='connected-user-count', detail=False,
            permission_classes=[permissions.IsAuthenticated, IsExpert])
    def connected_user_count(self, request):
        expert = request.user.expert_profile

        if expert.expert_type == ExpertType.TRAINER:
            total_count = User.objects.filter(regular_profile__connected_trainer=expert).count()
        elif expert.expert_type == ExpertType.NUTRITIONIST:
            total_count = User.objects.filter(regular_profile__connected_nutritionist=expert).count()
        else:
            total_count = 0

        return success_response("Số lượng người dùng đang kết nối", {"total_count": total_count})

    @action(methods=['get'], detail=True, url_path='user-detail',
            permission_classes=[permissions.IsAuthenticated, IsExpert])
    def connected_user_detail(self, request, pk=None):
        expert = request.user.expert_profile
        user_profile = get_object_or_404(RegularUser, pk=pk)

        if expert.expert_type == ExpertType.TRAINER and user_profile.connected_trainer != expert:
            return error_response("Bạn không có quyền xem người dùng này", status.HTTP_403_FORBIDDEN)
        if expert.expert_type == ExpertType.NUTRITIONIST and user_profile.connected_nutritionist != expert:
            return error_response("Bạn không có quyền xem người dùng này", status.HTTP_403_FORBIDDEN)

        user = user_profile.user
        serializer = UserSerializer(user)

        return success_response("Chi tiết người dùng kết nối", serializer.data)


    @action(methods=['get'], detail=True, url_path='detail',
                permission_classes=[permissions.IsAuthenticated, IsRegularUser])
    def expert_detail(self, request, pk=None):
        expert = get_object_or_404(Expert, pk=pk)
        serializer = ExpertSerializer(expert)
        return success_response("Chi tiết chuyên gia", serializer.data)

# ------HealthProfileViewSet------
class HealthProfileViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = HealthProfile.objects.all()
    serializer_class = HealthProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrExpertConnected]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'user':
            return HealthProfile.objects.filter(user__user=user)
        elif user.role == 'expert':
            reg_users = RegularUser.objects.filter(
                Q(connected_trainer__user=user) |
                Q(connected_nutritionist__user=user)
            )
            return HealthProfile.objects.filter(user__in=reg_users)
        return HealthProfile.objects.none()

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        reg_user = RegularUser.objects.get(user=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=reg_user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['get'], url_path='by-user/(?P<user_id>[^/.]+)', detail=False)
    def list_by_user(self, request, user_id=None):
        try:
            reg_user = RegularUser.objects.get(pk=user_id)
        except RegularUser.DoesNotExist:
            return Response({"detail": "Người dùng không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        dummy_instance = HealthProfile(user=reg_user)
        self.check_object_permissions(request, dummy_instance)

        try:
            latest_profile = HealthProfile.objects.filter(user=reg_user).latest('created_date')
        except HealthProfile.DoesNotExist:
            return Response({"detail": "Không tìm thấy hồ sơ sức khỏe."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(latest_profile)
        return Response(serializer.data)

    @action(methods=['get', 'patch'], url_path='current-profile', detail=False)
    def get_current_profile(self, request):
        try:
            reg_user = RegularUser.objects.get(user=request.user)
            latest_profile = reg_user.health_profiles.latest('created_date')
        except HealthProfile.DoesNotExist:
            return Response({"detail": "Không tìm thấy hồ sơ."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, latest_profile)

        if request.method == 'PATCH':
            if request.user.role != 'user':
                return Response({"detail": "Chỉ người dùng mới có thể cập nhật."}, status=status.HTTP_403_FORBIDDEN)
            serializer = self.get_serializer(latest_profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        serializer = self.get_serializer(latest_profile)
        return Response(serializer.data)

# ------HealthTrackingViewSet------
class HealthTrackingViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.DestroyAPIView):
    queryset = HealthTracking.objects.all()
    serializer_class = HealthTrackingSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrExpertConnected]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'user':
            return HealthTracking.objects.filter(user__user=user)
        elif user.role == 'expert':
            reg_users = RegularUser.objects.filter(
                Q(connected_trainer__user=user) |
                Q(connected_nutritionist__user=user)
            )
            return HealthTracking.objects.filter(user__in=reg_users)
        return HealthTracking.objects.none()

    def list(self, request):
        field = request.query_params.get("field")
        queryset = self.get_queryset()

        if field in ['bmi', 'steps', 'heart_rate', 'water_intake']:
            queryset = queryset.exclude(**{f"{field}__isnull": True})

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        reg_user = RegularUser.objects.get(user=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=reg_user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['get'], url_path='by-user/(?P<user_id>[^/.]+)', detail=False)
    def list_by_user(self, request, user_id=None):
        try:
            reg_user = RegularUser.objects.get(pk=user_id)
        except RegularUser.DoesNotExist:
            return Response({"detail": "Người dùng không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        dummy_instance = HealthTracking(user=reg_user)
        self.check_object_permissions(request, dummy_instance)

        try:
            latest_tracking = HealthTracking.objects.filter(user=reg_user).latest('date')
        except HealthTracking.DoesNotExist:
            return Response({"detail": "Không tìm thấy bản ghi theo dõi."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(latest_tracking)
        return Response(serializer.data)

    @action(methods=['get', 'patch'], url_path='current-tracking', detail=False)
    def get_current_tracking(self, request):
        try:
            reg_user = RegularUser.objects.get(user=request.user)
            latest_tracking = reg_user.healthtracking_set.latest('date')
        except HealthTracking.DoesNotExist:
            return Response({"detail": "Không tìm thấy bản ghi theo dõi sức khỏe."}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, latest_tracking)

        if request.method == 'PATCH':
            if request.user.role != 'user':
                return Response({"detail": "Chỉ người dùng mới có thể cập nhật."}, status=status.HTTP_403_FORBIDDEN)
            serializer = self.get_serializer(latest_tracking, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        serializer = self.get_serializer(latest_tracking)
        return Response(serializer.data)

# ------WorkoutViewSet------
class WorkoutViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = Workout.objects.all()
    serializer_class = WorkoutSerializer
    permission_classes = [permissions.IsAuthenticated, IsRegularUser | IsTrainer]

    def get_queryset(self):
        user = self.request.user
        goal = self.request.query_params.get('goal')
        search = self.request.query_params.get('search')
        qs = Workout.objects.none()

        if self.action == 'list':
            # Chỉ lấy bài tập public
            qs = Workout.objects.filter(is_public=True)

        elif self.action == 'suggested_by_expert':
            # User lấy bài tập được trainer gợi ý
            if user.role == 'user' and hasattr(user, 'regular_profile'):
                trainer = user.regular_profile.connected_trainer
                if trainer:
                    qs = Workout.objects.filter(
                        created_by=trainer.user,
                        suggested_to=user.regular_profile,
                        is_public=False
                    )

        elif self.action == 'own':
            # Lấy bài tập do user/expert tự tạo
            qs = Workout.objects.filter(created_by=user)

        # Lọc theo mục tiêu (goal)
        if goal:
            qs = qs.filter(goal=goal)

        # Tìm kiếm theo tên bài tập
        if search:
            qs = qs.filter(name__icontains=search)

        return qs

    def perform_create(self, serializer):
        user = self.request.user

        suggested_to_id = self.request.data.get('suggested_to')

        if user.role == 'expert' and hasattr(user, 'expert_profile'):
            if suggested_to_id:
                # Lấy User target
                target_user = get_object_or_404(User, id=suggested_to_id)
                regular_profile = getattr(target_user, 'regular_profile', None)

                # Kiểm tra kết nối trainer-user
                if not regular_profile or regular_profile.connected_trainer != user.expert_profile:
                    raise PermissionDenied("Bạn chỉ được gợi ý bài tập cho người dùng đã kết nối với bạn.")

                # Lưu bài tập gợi ý (private)
                serializer.save(created_by=user, is_public=False, suggested_to=regular_profile)
                return

        # Tạo bài tập bình thường (user hoặc expert không gợi ý cho ai)
        serializer.save(created_by=user, is_public=False)

    def retrieve(self, request, pk=None):
        workout = get_object_or_404(Workout, pk=pk)
        self.check_object_permissions(request, workout)
        return Response(self.get_serializer(workout).data)

    def _can_edit(self, user, workout):
        if workout.created_by == user:
            return True

        if user.role == 'user' and workout.suggested_to == getattr(user, 'regular_profile', None):
            return True

        return False

    def destroy(self, request, pk=None):
        workout = get_object_or_404(Workout, pk=pk)

        if not self._can_edit(request.user, workout):
            raise PermissionDenied("Bạn không có quyền xóa bài tập này.")

        if workout.workoutsession_set.exists():
            raise PermissionDenied("Bài tập đang được sử dụng trong kế hoạch, không thể xóa.")

        workout.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def partial_update(self, request, pk=None):  # PATCH
        workout = get_object_or_404(Workout, pk=pk)
        if not self._can_edit(request.user, workout):
            raise PermissionDenied("Bạn không có quyền chỉnh sửa bài tập này.")
        serializer = self.get_serializer(workout, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def list(self, request):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "Chưa có bài tập nào."}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='own')
    def own(self, request):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "Chưa có bài tập nào bạn đã tạo."}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='suggested-by-expert')
    def suggested_by_expert(self, request):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "Chưa có bài tập nào được chuyên gia gợi ý."}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

# ------WorkoutPlanViewSet------
class WorkoutPlanViewSet(viewsets.ViewSet, generics.CreateAPIView):
    serializer_class = WorkoutPlanSerializer
    permission_classes = [permissions.IsAuthenticated, IsRegularUser]

    def get_queryset(self):
        user = self.request.user
        regular_profile = getattr(user, 'regular_profile', None)
        if not regular_profile:
            return WorkoutPlan.objects.none()
        return WorkoutPlan.objects.filter(user=regular_profile)

    def list(self, request):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "Chưa có kế hoạch luyện tập nào."}, status=status.HTTP_200_OK)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = self.get_queryset()
        plan = get_object_or_404(queryset, pk=pk)
        serializer = WorkoutPlanSerializer(plan)
        return Response(serializer.data)

    def create(self, request):
        serializer = WorkoutPlanSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        return Response(WorkoutPlanSerializer(plan).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):  # PATCH only
        plan = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.serializer_class(plan, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        queryset = self.get_queryset()
        plan = get_object_or_404(queryset, pk=pk)
        plan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# ------MealViewSet-------
class MealViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = Meal.objects.all()
    serializer_class = MealSerializer
    permission_classes = [permissions.IsAuthenticated, IsRegularUser | IsExpert]

    def get_queryset(self):
        user = self.request.user
        goal = self.request.query_params.get('goal')
        search = self.request.query_params.get('search')
        qs = Meal.objects.none()

        if self.action == 'list':
            qs = Meal.objects.filter(is_public=True)
        elif self.action == 'suggested_by_expert':
            if user.role == 'user' and hasattr(user, 'regular_profile'):
                nutritionist = user.regular_profile.connected_nutritionist
                if nutritionist:
                    qs = Meal.objects.filter(
                        created_by=nutritionist.user,
                        suggested_to=user.regular_profile,
                        is_public=False
                    )
        elif self.action == 'own':
            qs = Meal.objects.filter(created_by=user)

        if goal:
            qs = qs.filter(goal=goal)
        if search:
            qs = qs.filter(name__icontains=search)

        return qs

    def perform_create(self, serializer):
        user = self.request.user
        suggested_to_id = self.request.data.get('suggested_to')

        if user.role == 'expert' and hasattr(user, 'expert_profile'):
            if suggested_to_id:
                target_user = get_object_or_404(User, id=suggested_to_id)
                regular_profile = getattr(target_user, 'regular_profile', None)

                if not regular_profile or regular_profile.connected_nutritionist != user.expert_profile:
                    raise PermissionDenied("Bạn chỉ được gợi ý bữa ăn cho người dùng đã kết nối với bạn.")

                serializer.save(created_by=user, is_public=False, suggested_to=regular_profile)
                return

        serializer.save(created_by=user, is_public=False)

    def retrieve(self, request, pk=None):
        meal = get_object_or_404(Meal, pk=pk)
        self.check_object_permissions(request, meal)
        return Response(self.get_serializer(meal).data)

    def _can_edit(self, user, meal):
        if meal.created_by == user:
            return True

        if user.role == 'user' and meal.suggested_to == getattr(user, 'regular_profile', None):
            return True

        return False

    def destroy(self, request, pk=None):
        meal = get_object_or_404(Meal, pk=pk)

        if not self._can_edit(request.user, meal):
            raise PermissionDenied("Bạn không có quyền xóa bữa ăn này.")

        if meal.mealplan_meals.exists():
            raise PermissionDenied("Bữa ăn đang được sử dụng trong kế hoạch, không thể xóa.")

        meal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def partial_update(self, request, pk=None):
        meal = get_object_or_404(Meal, pk=pk)

        if not self._can_edit(request.user, meal):
            raise PermissionDenied("Bạn không có quyền chỉnh sửa bữa ăn này.")

        serializer = self.get_serializer(meal, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def list(self, request):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "Chưa có bữa ăn nào."}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='own')
    def own(self, request):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "Chưa có bữa ăn nào bạn đã tạo."}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='suggested-by-expert')
    def suggested_by_expert(self, request):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "Chưa có bữa ăn nào được chuyên gia gợi ý."}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ------MealPlanViewSet------
class MealPlanViewSet(viewsets.ViewSet, generics.CreateAPIView):
    serializer_class = MealPlanSerializer
    permission_classes = [permissions.IsAuthenticated, IsRegularUser]

    def get_queryset(self):
        user = self.request.user
        regular_profile = getattr(user, 'regular_profile', None)
        if not regular_profile:
            return MealPlan.objects.none()
        return MealPlan.objects.filter(user=regular_profile)

    def list(self, request):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "Chưa có kế hoạch dinh dưỡng nào."}, status=status.HTTP_200_OK)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        plan = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.serializer_class(plan)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        return Response(self.serializer_class(plan).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):  # PATCH only
        plan = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.serializer_class(plan, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        plan = get_object_or_404(self.get_queryset(), pk=pk)
        plan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# ------HealthJournalViewSet------
class HealthJournalViewSet(viewsets.ViewSet,
                           generics.ListAPIView,
                           generics.CreateAPIView,
                           generics.RetrieveAPIView,
                           generics.UpdateAPIView,
                           generics.DestroyAPIView):
    serializer_class = HealthJournalSerializer
    permission_classes = [permissions.IsAuthenticated, IsRegularUser]

    def get_queryset(self):
        user = self.request.user
        regular_profile = getattr(user, 'regular_profile', None)
        if not regular_profile:
            return HealthJournal.objects.none()
        return HealthJournal.objects.filter(user=regular_profile, active=True)

    def list(self, request):
        queryset = self.get_queryset().order_by('-date')
        if not queryset.exists():
            return Response({"detail": "Chưa có nhật ký sức khỏe nào."}, status=status.HTTP_200_OK)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        journal = serializer.save()
        return Response(self.serializer_class(journal).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        journal = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.serializer_class(journal)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):  # PATCH only
        journal = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.serializer_class(journal, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        journal = get_object_or_404(self.get_queryset(), pk=pk)
        journal.active = False  # Soft delete
        journal.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

# -------ReminderViewSet------
class ReminderViewSet(viewsets.ViewSet,
                      generics.ListAPIView,
                      generics.CreateAPIView,
                      generics.RetrieveAPIView,
                      generics.DestroyAPIView):  # Không hỗ trợ PUT (UpdateAPIView)
    serializer_class = ReminderSerializer
    permission_classes = [permissions.IsAuthenticated, IsRegularUser]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Reminder.objects.none()
        return Reminder.objects.filter(user=self.request.user.regular_profile).order_by('send_at')

    def list(self, request):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "Chưa có nhắc nhở nào."}, status=status.HTTP_200_OK)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        reminder = serializer.save()
        return Response(self.serializer_class(reminder).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        reminder = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.serializer_class(reminder)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):  # PATCH (update một phần)
        reminder = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.serializer_class(reminder, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        reminder = get_object_or_404(self.get_queryset(), pk=pk)
        reminder.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# ------ReviewViewSet------
class ReviewViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.ListAPIView, generics.RetrieveAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, CanReviewExpert]

    def get_queryset(self):
        # Lấy tất cả review của một chuyên gia
        expert_id = self.kwargs.get('expert_pk')
        return Review.objects.filter(expert_id=expert_id).order_by('-created_at')

    def list(self, request, expert_pk=None):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, expert_pk=None):
        user = request.user
        expert = get_object_or_404(Expert, pk=expert_pk)

        # Kiểm tra đã đánh giá chưa
        if Review.objects.filter(expert=expert, reviewer=user.regular_profile).exists():
            return Response({"detail": "Bạn đã đánh giá chuyên gia này."}, status=status.HTTP_400_BAD_REQUEST)

        # Kiểm tra quyền đánh giá (sử dụng permission CanReviewExpert)
        self.check_object_permissions(request, expert)

        data = request.data.copy()
        data['expert'] = expert.id
        data['reviewer'] = user.regular_profile.id

        serializer = self.serializer_class(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(self.serializer_class(review).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get', 'patch'], url_path='my-review')
    def my_review(self, request, expert_pk=None):
        user = request.user
        expert = get_object_or_404(Expert, pk=expert_pk)
        try:
            review = Review.objects.get(expert=expert, reviewer=user.regular_profile)
        except Review.DoesNotExist:
            if request.method == 'GET':
                return Response({"detail": "Bạn chưa đánh giá chuyên gia này."}, status=404)
            else:
                return Response({"detail": "Không thể chỉnh sửa đánh giá vì chưa có đánh giá."}, status=400)

        if request.method == 'GET':
            serializer = self.serializer_class(review)
            return Response(serializer.data)

        elif request.method == 'PATCH':
            # Kiểm tra quyền (nếu cần, thường người đánh giá có quyền sửa đánh giá của mình)
            serializer = self.serializer_class(review, data=request.data, partial=True, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
# ------ChatMessageViewSet-------
class ChatMessageViewSet(viewsets.ViewSet,
                         generics.CreateAPIView,
                         generics.ListAPIView,
                         generics.RetrieveAPIView,
                         generics.DestroyAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ChatMessage.objects.none()

        user = self.request.user
        receiver_id = self.request.query_params.get('receiver_id')

        if receiver_id:
            return ChatMessage.objects.filter(
                (Q(sender=user) & Q(receiver__id=receiver_id)) |
                (Q(sender__id=receiver_id) & Q(receiver=user))
            ).order_by('created_at')
        else:
            return ChatMessage.objects.filter(
                Q(sender=user) | Q(receiver=user)
            ).order_by('-created_at')

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        sender = request.user
        receiver_id = serializer.validated_data.get('receiver').id

        # Kiểm tra người gửi là user thường hoặc expert
        if hasattr(sender, 'regular_profile'):
            regular_user = sender.regular_profile

            if regular_user.tracking_mode != 'connected':
                return Response({"detail": "Bạn chưa kết nối với chuyên gia."}, status=status.HTTP_400_BAD_REQUEST)

            connected_experts = [regular_user.connected_trainer, regular_user.connected_nutritionist]
            if not any(expert and expert.user.id == receiver_id for expert in connected_experts):
                return Response({"detail": "Người nhận không phải chuyên gia bạn đang kết nối."}, status=status.HTTP_400_BAD_REQUEST)

        elif hasattr(sender, 'expert_profile'):
            expert = sender.expert_profile
            clients = RegularUser.objects.filter(
                Q(connected_trainer=expert) | Q(connected_nutritionist=expert)
            )
            if not clients.filter(user_id=receiver_id).exists():
                return Response({"detail": "Người nhận không phải người dùng kết nối với bạn."}, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({"detail": "Vai trò không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)

        message = serializer.save()
        return Response(self.serializer_class(message).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        message = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.serializer_class(message)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        message = get_object_or_404(self.get_queryset(), pk=pk)

        if message.sender != request.user:
            raise PermissionDenied("Chỉ người gửi được sửa tin nhắn.")

        if message.is_revoked:
            return Response({"detail": "Tin nhắn đã thu hồi, không thể sửa."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(message, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def destroy(self, request, pk=None):
        message = get_object_or_404(self.get_queryset(), pk=pk)

        if message.sender != request.user:
            raise PermissionDenied("Chỉ người gửi được xóa/thu hồi tin nhắn.")

        message.is_revoked = True
        message.save()

        return Response({"detail": "Tin nhắn đã được thu hồi."}, status=status.HTTP_200_OK)

# ------ReportViewSet------
class ReportViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_user_regular_profile(self, user):
        return getattr(user, 'regular_profile', None)

    def is_expert_connected_to_user(self, expert_user, regular_user):
        if not hasattr(expert_user, 'expert_profile'):
            return False
        expert = expert_user.expert_profile
        return (regular_user.connected_trainer == expert or
                regular_user.connected_nutritionist == expert)

    def _filter_time_range(self, queryset, period):
        today = now().date()
        if period == 'week':
            start_date = today - timedelta(days=today.weekday())
        elif period == 'month':
            start_date = today.replace(day=1)
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
        else:
            start_date = None

        if start_date:
            queryset = queryset.filter(date__gte=start_date, date__lte=today)
        return queryset

    @action(detail=False, methods=['get'], url_path='user-health-progress')
    def user_health_progress(self, request):
        user = request.user
        regular_profile = self.get_user_regular_profile(user)
        if not regular_profile:
            return Response({"detail": "User không có profile theo dõi"}, status=status.HTTP_400_BAD_REQUEST)

        period = request.query_params.get('period', 'week')
        health_tracking_qs = regular_profile.health_tracking.all()
        health_tracking_qs = self._filter_time_range(health_tracking_qs, period)

        total_steps = health_tracking_qs.aggregate(total_steps=Sum('steps'))['total_steps'] or 0
        avg_heart_rate = health_tracking_qs.aggregate(avg_hr=Avg('heart_rate'))['avg_hr'] or 0
        total_water = health_tracking_qs.aggregate(total_water=Sum('water_intake'))['total_water'] or 0

        # Lấy BMI từ bản ghi mới nhất trong khoảng thời gian
        latest_tracking = health_tracking_qs.order_by('-date').first()
        bmi = None
        if latest_tracking and latest_tracking.height and latest_tracking.weight:
            height_m = latest_tracking.height / 100  # cm -> m
            bmi = round(latest_tracking.weight / (height_m ** 2), 2)

        return Response({
            "steps": total_steps,
            "avg_heart_rate": avg_heart_rate,
            "water_intake": total_water,
            "bmi": bmi
        })

    @action(detail=False, methods=['get'], url_path='user-workout-stats')
    def user_workout_stats(self, request):
        """
        Người dùng xem thống kê luyện tập theo tuần/tháng
        """
        user = request.user
        regular_profile = self.get_user_regular_profile(user)
        if not regular_profile:
            return Response({"detail": "User không có profile theo dõi"}, status=status.HTTP_400_BAD_REQUEST)

        period = request.query_params.get('period', 'week')
        if period not in ['week', 'month']:
            return Response({"detail": "Chỉ cho phép tuần hoặc tháng cho thống kê luyện tập"}, status=status.HTTP_400_BAD_REQUEST)

        workout_sessions = WorkoutSession.objects.filter(workout_plan__user=regular_profile)
        workout_sessions = self._filter_time_range(workout_sessions, period)

        total_duration = workout_sessions.aggregate(total_duration=Sum('duration'))['total_duration'] or 0
        total_calories = workout_sessions.aggregate(
            total_calories=Sum('workout__calories_burned')
        )['total_calories'] or 0

        return Response({
            "total_workout_duration": total_duration,
            "total_calories_burned": total_calories,
        })

    @action(detail=False, methods=['get'], url_path='expert-client-health-progress')
    def expert_client_health_progress(self, request):
        expert_user = request.user
        if not hasattr(expert_user, 'expert_profile'):
            return Response({"detail": "Bạn không phải chuyên gia"}, status=status.HTTP_403_FORBIDDEN)

        client_id = request.query_params.get('client_id')
        if not client_id:
            return Response({"detail": "Thiếu client_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client_regular_user = RegularUser.objects.get(id=client_id)
        except RegularUser.DoesNotExist:
            return Response({"detail": "Client không tồn tại"}, status=status.HTTP_404_NOT_FOUND)

        if not self.is_expert_connected_to_user(expert_user, client_regular_user):
            return Response({"detail": "Bạn không được phép xem dữ liệu của client này"},
                            status=status.HTTP_403_FORBIDDEN)

        period = request.query_params.get('period', 'week')
        health_tracking_qs = client_regular_user.health_tracking.all()
        health_tracking_qs = self._filter_time_range(health_tracking_qs, period)

        total_steps = health_tracking_qs.aggregate(total_steps=Sum('steps'))['total_steps'] or 0
        avg_heart_rate = health_tracking_qs.aggregate(avg_hr=Avg('heart_rate'))['avg_hr'] or 0
        total_water = health_tracking_qs.aggregate(total_water=Sum('water_intake'))['total_water'] or 0

        latest_tracking = health_tracking_qs.order_by('-date').first()
        bmi = None
        if latest_tracking and latest_tracking.height and latest_tracking.weight:
            height_m = latest_tracking.height / 100
            bmi = round(latest_tracking.weight / (height_m ** 2), 2)

        return Response({
            "steps": total_steps,
            "avg_heart_rate": avg_heart_rate,
            "water_intake": total_water,
            "bmi": bmi
        })
