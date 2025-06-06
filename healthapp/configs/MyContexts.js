import { createContext } from "react";

// Lưu thông tin người dùng đang đăng nhập (user object)
export const MyUserContext = createContext(null);

// Hàm dispatch để cập nhật trạng thái (login, logout)
export const MyDispatchContext = createContext(null);
