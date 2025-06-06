// navigators/ExpertTabNavigator.js
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Icon } from "react-native-paper";

import HomeScreen from "../screens/Expert/HomeScreen";
import ClientListScreen from "../screens/Expert/ClientListScreen";
import ExpertChatBox from "../components/ExpertChatBox"; // hoặc nếu có màn hình chat riêng thì import màn hình đó
import ProfileScreen from "../screens/Expert/ProfileScreen";

const Tab = createBottomTabNavigator();

const ExpertTabNavigator = () => {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }}>
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          title: "Trang chủ",
          tabBarIcon: () => <Icon source="home" size={24} />,
        }}
      />
      <Tab.Screen
        name="ClientList"
        component={ClientListScreen}
        options={{
          title: "Danh sách khách",
          tabBarIcon: () => <Icon source="account-group" size={24} />,
        }}
      />
      <Tab.Screen
        name="Chat"
        component={ExpertChatBox} // nếu có màn hình chat, thay bằng màn hình đó
        options={{
          title: "Chat",
          tabBarIcon: () => <Icon source="chat" size={24} />,
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          title: "Hồ sơ",
          tabBarIcon: () => <Icon source="account" size={24} />,
        }}
      />
    </Tab.Navigator>
  );
};

export default ExpertTabNavigator;
