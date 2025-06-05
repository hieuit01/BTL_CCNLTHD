from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (UserViewSet, ExpertViewSet, HealthProfileViewSet, HealthTrackingViewSet, WorkoutViewSet,
                    WorkoutPlanViewSet, MealViewSet, MealPlanViewSet, HealthJournalViewSet, ReminderViewSet,
                    ChatMessageViewSet, ReviewViewSet, ReportViewSet)

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('experts', ExpertViewSet, basename='expert')
router.register(r'health-profiles', HealthProfileViewSet, basename='health-profile')
router.register(r'health-trackings', HealthTrackingViewSet, basename='health-tracking')
router.register(r'workouts', WorkoutViewSet, basename='workout')
router.register(r'workout-plans', WorkoutPlanViewSet, basename='workoutplan')
router.register(r'meals', MealViewSet, basename='meal')
router.register(r'meal-plans', MealPlanViewSet, basename='meal-plan')
router.register(r'health-journals', HealthJournalViewSet, basename='health-journal')
router.register(r'reminders', ReminderViewSet, basename='reminder')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'chats', ChatMessageViewSet, basename='chat')
router.register(r'reports', ReportViewSet, basename='reports')

urlpatterns = [
    path('', include(router.urls)),
]
