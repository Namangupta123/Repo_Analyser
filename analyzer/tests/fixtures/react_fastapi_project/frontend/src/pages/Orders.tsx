import { getOrders } from "../api/orders";
import OrderCard from "@/components/OrderCard";

export default function Orders() {
  return <OrderCard order={getOrders()} />;
}
