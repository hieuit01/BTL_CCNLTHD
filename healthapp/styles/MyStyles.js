import { StyleSheet } from "react-native";

const MyStyles = StyleSheet.create({
  m: {
    marginVertical: 10,
  },

  container: {
    flex: 1,
    padding: 20,
    backgroundColor: "#fff",
  },

  center: {
    justifyContent: "center",
    alignItems: "center",
  },

  avatar: {
    width: 100,
    height: 100,
    borderRadius: 50,
    marginVertical: 10,
  },

  input: {
    backgroundColor: "white",
    marginBottom: 10,
  },

  button: {
    marginVertical: 10,
    paddingVertical: 10,
    borderRadius: 5,
  },

  card: {
    backgroundColor: "#f9f9f9",
    borderRadius: 10,
    padding: 15,
    marginVertical: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 5,
    elevation: 3,
  },

  title: {
    fontSize: 22,
    fontWeight: "bold",
    marginBottom: 10,
  },

  subtitle: {
    fontSize: 16,
    color: "#555",
    marginBottom: 5,
  },

  row: {
    flexDirection: "row",
    alignItems: "center",
  },

  spaceBetween: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  divider: {
    height: 1,
    backgroundColor: "#ddd",
    marginVertical: 10,
  },
});

export default MyStyles;
