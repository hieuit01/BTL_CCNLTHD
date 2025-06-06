import { NavigationContainer } from "@react-navigation/native";
import { useReducer, useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { MyUserContext, MyDispatchContext } from "./configs/MyContexts";
import MyUserReducer from "./reducers/MyUserReducer";
import AuthNavigator from "./navigators/AuthNavigator";
import UserTabNavigator from "./navigators/UserTabNavigator";
import ExpertTabNavigator from "./navigators/ExpertTabNavigator";
import { authApis, endpoints } from "./configs/Apis";

const App = () => {
  const [user, dispatch] = useReducer(MyUserReducer, null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
      try {
        const token = await AsyncStorage.getItem("token");
        if (token) {
          let res = await authApis(token).get(endpoints["current_user"]);
          dispatch({ type: "login", payload: res.data });
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadUser();
  }, []);

  if (loading) return null;

  let mainNav = <AuthNavigator />;
  if (user?.role === "user") mainNav = <UserTabNavigator />;
  else if (user?.role === "expert") mainNav = <ExpertTabNavigator />;

  return (
    <MyUserContext.Provider value={user}>
      <MyDispatchContext.Provider value={dispatch}>
        <NavigationContainer>
          {mainNav}
        </NavigationContainer>
      </MyDispatchContext.Provider>
    </MyUserContext.Provider>
  );
};

export default App;
