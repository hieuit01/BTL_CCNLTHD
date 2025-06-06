import { useContext, useState } from "react";
import { ScrollView, View, Text } from "react-native";
import { TextInput, Button, HelperText } from "react-native-paper";
import { useNavigation } from "@react-navigation/native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import Apis, { authApis, endpoints } from "../../configs/Apis";
import { MyDispatchContext } from "../../configs/MyContexts";
import MyStyles from "../../styles/MyStyles";

const LoginScreen = () => {
  const [user, setUser] = useState({});
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);
  const dispatch = useContext(MyDispatchContext);
  const nav = useNavigation();

  const info = [
    { label: "Tên đăng nhập", field: "username", secureTextEntry: false, icon: "account" },
    { label: "Mật khẩu", field: "password", secureTextEntry: true, icon: "eye" },
  ];

  const setState = (value, field) => {
    setUser({ ...user, [field]: value });
  };

  const validate = () => {
    for (let i of info)
      if (!user[i.field] || user[i.field].trim() === "") {
        setMsg(`Vui lòng nhập ${i.label}`);
        return false;
      }
    return true;
  };

  const login = async () => {
    if (!validate()) return;

    try {
      setLoading(true);
      let res = await Apis.post(endpoints["login"], {
        ...user,
        client_id: "fNRZSHmkWnbWx5XXcpaizYVJA0fhSXgK0VrEwhJF",
        client_secret: "Tcu9tld1R3Cx44os9ctpnEymwM72c4X0STvJCaCqhacFJt31sYBnDpfknJXewzFqDxeUwPrG2oCyRbct8rvWGg1tbjl08aJBA8LSUF8VkuCmHKw4rtVkyaTe8RidkOxH",
        grant_type: "password",
      });

      const token = res.data.access_token;
      await AsyncStorage.setItem("token", token);

      const userRes = await authApis(token).get(endpoints["current_user"]);
      const currentUser = userRes.data;

      dispatch({ type: "login", payload: currentUser });

      if (currentUser.role === "user") {
        nav.reset({ index: 0, routes: [{ name: "UserMain" }] });
      } else if (currentUser.role === "expert") {
        nav.reset({ index: 0, routes: [{ name: "ExpertMain" }] });
      }
    } catch (err) {
      console.error(err);
      setMsg("Tên đăng nhập hoặc mật khẩu không đúng.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={MyStyles.container}>
      <Text style={MyStyles.title}>🧑‍💻 Đăng nhập</Text>

      {msg && (
        <HelperText type="error" visible={true} style={MyStyles.m}>
          {msg}
        </HelperText>
      )}

      {info.map((i) => (
        <TextInput
          key={i.field}
          label={i.label}
          value={user[i.field]}
          onChangeText={(t) => setState(t, i.field)}
          secureTextEntry={i.secureTextEntry}
          right={<TextInput.Icon icon={i.icon} />}
          mode="outlined"
          style={[MyStyles.input, MyStyles.m]}
        />
      ))}

      <Button
        mode="contained"
        onPress={login}
        loading={loading}
        disabled={loading}
        style={MyStyles.button}
      >
        Đăng nhập
      </Button>
    </ScrollView>
  );
};

export default LoginScreen;
