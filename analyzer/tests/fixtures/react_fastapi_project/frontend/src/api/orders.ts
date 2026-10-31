import axios from "axios";

export const getOrders = () => axios.get("/orders");
