const UserTabNavigator = () => {
  return (
    <Tab.Navigator 
      initialRouteName="Home"   // <--- Thêm dòng này để mặc định chọn tab Home
      screenOptions={{ headerShown: false }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          title: "Trang chủ",
          tabBarIcon: () => <Icon source="home" size={24} />,
        }}
      />
      <Tab.Screen
        name="Tracking"
        component={TrackingScreen}
        options={{
          title: "Theo dõi",
          tabBarIcon: () => <Icon source="chart-line" size={24} />,
        }}
      />
      <Tab.Screen
        name="Plan"
        component={PlanScreen}
        options={{
          title: "Kế hoạch",
          tabBarIcon: () => <Icon source="calendar" size={24} />,
        }}
      />
      <Tab.Screen
        name="Journal"
        component={JournalScreen}
        options={{
          title: "Nhật ký",
          tabBarIcon: () => <Icon source="book" size={24} />,
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          title: "Cá nhân",
          tabBarIcon: () => <Icon source="account" size={24} />,
        }}
      />
    </Tab.Navigator>
  );
};
