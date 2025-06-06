import React, { useContext, useEffect, useState } from "react";
import { View, Text, ScrollView, StyleSheet, Image, TouchableOpacity } from "react-native";
import moment from "moment";
import "moment/locale/vi";

import { authApis, endpoints } from "../../configs/Apis";
import { MyUserContext } from "../../configs/MyContexts";

const HomeScreen = () => {
  const user = useContext(MyUserContext);
  const [reminders, setReminders] = useState([]);
  const [healthStats, setHealthStats] = useState(null);
  const [connectedExperts, setConnectedExperts] = useState(null);
  const [todayWorkout, setTodayWorkout] = useState([]);
  const [todayMeals, setTodayMeals] = useState([]);
  const [suggestedWorkouts, setSuggestedWorkouts] = useState([]);
  const [suggestedMeals, setSuggestedMeals] = useState([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const resReminder = await authApis(user.token).get(endpoints.reminders);
        const resHealth = await authApis(user.token).get(endpoints.current_health_tracking);
        const resExpert = await authApis(user.token).get(endpoints.connected_users);
        const resWorkout = await authApis(user.token).get(endpoints.workout_plans, { params: { today: true } });
        const resMeal = await authApis(user.token).get(endpoints.meal_plans, { params: { today: true } });
        const resSuggWorkout = await authApis(user.token).get(endpoints.suggested_workouts);
        const resSuggMeal = await authApis(user.token).get(endpoints.suggested_meals);

        setReminders(resReminder.data || []);
        setHealthStats(resHealth.data || {});
        setConnectedExperts(resExpert.data || {});
        setTodayWorkout(resWorkout.data || []);
        setTodayMeals(resMeal.data || []);
        setSuggestedWorkouts(resSuggWorkout.data || []);
        setSuggestedMeals(resSuggMeal.data || []);
      } catch (err) {
        console.error(err);
      }
    };

    loadData();
  }, []);

  const renderReminder = () => reminders.map((r, i) => (
    <Text key={i}>- {moment(r.time, "HH:mm:ss").format("HH:mm")} {r.title}</Text>
  ));

  const renderHealthStat = (label, value, unit = "") => (
    <Text>{label}: {value !== null ? `${value} ${unit}` : "Chưa cập nhật"}</Text>
  );

  const renderExpert = (type, expert) => (
    <View style={styles.expertBox}>
      <Image source={{ uri: expert?.avatar }} style={styles.avatar} />
      <Text>{expert?.full_name}</Text>
      <TouchableOpacity>
        <Text style={styles.chatBubble}>💬</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>👋 Xin chào, {user?.last_name} {user?.first_name}</Text>
      <Text>📅 Ngày hôm nay: {moment().format("DD/MM/YYYY")}</Text>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>🔔 Nhắc nhở hôm nay:</Text>
        {reminders.length ? renderReminder() : <Text>Không có nhắc nhở</Text>}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>📊 Chỉ số sức khỏe hôm nay:</Text>
        {renderHealthStat("BMI", healthStats?.bmi)}
        {renderHealthStat("Số bước", healthStats?.step_count, "bước")}
        {renderHealthStat("Nhịp tim", healthStats?.heart_rate, "bpm")}
        {renderHealthStat("Nước uống", healthStats?.water_intake, "ml")}
      </View>

      {user?.tracking_mode === "expert_connection" && connectedExperts && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>👥 Chuyên gia đang kết nối:</Text>
          {connectedExperts.trainer && renderExpert("HLV", connectedExperts.trainer)}
          {connectedExperts.nutritionist && renderExpert("Dinh dưỡng", connectedExperts.nutritionist)}
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>🔥 Kế hoạch hôm nay:</Text>
        {todayWorkout.length > 0 ? todayWorkout.map((w, i) => (
          <Text key={i}>- 🏋️ {w.title}</Text>
        )) : <Text>Không có bài tập hôm nay</Text>}
        {todayMeals.length > 0 ? todayMeals.map((m, i) => (
          <Text key={i}>- 🍽️ {m.title}</Text>
        )) : <Text>Không có thực đơn hôm nay</Text>}
      </View>

      {user?.tracking_mode === "expert_connection" && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>🎯 Gợi ý từ chuyên gia:</Text>
          {suggestedWorkouts.length > 0 ? (
            <TouchableOpacity><Text>📋 Xem bài tập gợi ý</Text></TouchableOpacity>
          ) : <Text>Chuyên gia chưa gợi ý bài tập</Text>}
          {suggestedMeals.length > 0 ? (
            <TouchableOpacity><Text>🍽️ Xem thực đơn gợi ý</Text></TouchableOpacity>
          ) : <Text>Chuyên gia chưa gợi ý thực đơn</Text>}
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { padding: 16 },
  header: { fontSize: 20, fontWeight: "bold", marginBottom: 8 },
  section: { marginTop: 16 },
  sectionTitle: { fontWeight: "bold", marginBottom: 4 },
  expertBox: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  avatar: { width: 40, height: 40, borderRadius: 20, marginRight: 8 },
  chatBubble: { fontSize: 18 }
});

export default HomeScreen;
