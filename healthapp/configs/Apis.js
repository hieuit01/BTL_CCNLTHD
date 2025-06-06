import axios from "axios"

const BASE_URL = "http://192.168.1.8:8000/";

export const endpoints = {
    // User
    'register_user': '/users/',
    'login': '/o/token/',
    'current_user': '/users/current-user/',
    'user_tracking': '/users/tracking/',

    // Expert
    'register_experts': '/experts/',
    'current_expert': '/experts/current-expert/',
    'trainers': '/experts/trainers/',
    'nutritionists': '/experts/nutritionists/',
    'connected_users': '/experts/connected-users/',
    'connected_user_count': '/experts/connected-user-count/',
    'expert_detail': (id) => `/experts/${id}/detail/`,
    'connected_user_detail': (id) => `/experts/${id}/user-detail/`,

    // Health Profile
    'health_profiles': '/health-profiles/',
    'health_profile_by_user': (userId) => `/health-profiles/by-user/${userId}/`,
    'current_health_profile': '/health-profiles/current-profile/',

    // Health Tracking
    'health_trackings': '/health-trackings/',
    'health_tracking_by_user': (userId) => `/health-trackings/by-user/${userId}/`,
    'current_health_tracking': '/health-trackings/current-tracking/',

    // Workouts
    'workouts': '/workouts/',
    'own_workouts': '/workouts/own/',
    'suggested_workouts': '/workouts/suggested-by-expert/',
    'workout_detail': (id) => `/workouts/${id}/`,

    // Workout Plans
    'workout_plans': '/workout-plans/',
    'workout_plan_detail': (id) => `/workout-plans/${id}/`,

    // Meals
    'meals': '/meals/',
    'own_meals': '/meals/own/',
    'suggested_meals': '/meals/suggested-by-expert/',
    'meal_detail': (id) => `/meals/${id}/`,

    // Meal Plans
    'meal_plans': '/meal-plans/',
    'meal_plan_detail': (id) => `/meal-plans/${id}/`,

    // Health Journals
    'health_journals': '/health-journals/',
    'health_journal_detail': (id) => `/health-journals/${id}/`,

    // Reminders
    'reminders': '/reminders/',
    'reminder_detail': (id) => `/reminders/${id}/`,

    // Reviews
    'expert_reviews': (expertId) => `/reviews/${expertId}/`,
    'my_review': (expertId) => `/reviews/${expertId}/my-review/`,

    // Chats
    'chats': '/chats/',
    'chat_detail': (id) => `/chats/${id}/`,

    // Reports
    'user_health_progress': '/reports/user-health-progress/',
    'user_workout_stats': '/reports/user-workout-stats/',
    'user_meal_stats': '/reports/user-meal-stats/',
    'expert_client_progress': '/reports/expert-client-progress/',
}

export const authApis = (token) => {
    return axios.create({
        baseURL: BASE_URL,
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
}

export default axios.create({
    baseURL: BASE_URL
});
