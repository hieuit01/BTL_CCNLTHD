import AsyncStorage from "@react-native-async-storage/async-storage";

const MyUserReducer = (current, action) => {
  switch (action.type) {
    case "login":
      return action.payload;

    case "logout":
      AsyncStorage.removeItem("token");
      return null;

    default:
      return current;
  }
};

export default MyUserReducer;
