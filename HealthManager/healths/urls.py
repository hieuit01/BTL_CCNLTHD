from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, TrainerViewSet, NutritionistViewSet, HealthProfileViewSet, HealthTrackingViewSet, \
    WorkoutViewSet, WorkoutPlanViewSet, WorkoutSessionViewSet, MealViewSet, MealPlanViewSet, MealPlanMealViewSet, \
    HealthJournalViewSet, ReminderViewSet, ChatMessageViewSet
from django.contrib.auth import views as auth_views
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'trainers', TrainerViewSet, basename='trainer')
router.register(r'nutritionists', NutritionistViewSet, basename='nutritionist')
router.register(r'health-profiles', HealthProfileViewSet, basename='health-profile')
router.register(r'health-tracking', HealthTrackingViewSet, basename='health-tracking')
router.register(r'workouts', WorkoutViewSet, basename='workout')
router.register(r'workout-plans', WorkoutPlanViewSet, basename='workout-plan')
router.register(r'workout-sessions', WorkoutSessionViewSet, basename='workout-session')
router.register(r'meals', MealViewSet, basename='meal')
router.register(r'meal-plans', MealPlanViewSet, basename='meal-plan')
router.register(r'meal-plan-meals', MealPlanMealViewSet, basename='meal-plan-meal')
router.register(r'health-journals', HealthJournalViewSet, basename='health-journal')
router.register(r'reminders', ReminderViewSet, basename='reminder')
router.register(r'chat-messages', ChatMessageViewSet, basename='chat-message')
urlpatterns = [
    path('api-auth/', include('rest_framework.urls')),
    path('', include(router.urls)),
]
