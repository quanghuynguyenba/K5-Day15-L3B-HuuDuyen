import ExploreOutlined from "@mui/icons-material/ExploreOutlined";
import AddRounded from "@mui/icons-material/AddRounded";
import SpaceDashboardOutlined from "@mui/icons-material/SpaceDashboardOutlined";
import ChatBubbleOutlineRounded from "@mui/icons-material/ChatBubbleOutlineRounded";
import PlaceOutlined from "@mui/icons-material/PlaceOutlined";
import CloudOutlined from "@mui/icons-material/CloudOutlined";
import RestaurantOutlined from "@mui/icons-material/RestaurantOutlined";
import AccountBalanceOutlined from "@mui/icons-material/AccountBalanceOutlined";
import FamilyRestroomOutlined from "@mui/icons-material/FamilyRestroomOutlined";
import VolumeUpOutlined from "@mui/icons-material/VolumeUpOutlined";
import SendRounded from "@mui/icons-material/SendRounded";
import ScheduleRounded from "@mui/icons-material/ScheduleRounded";
import CloseRounded from "@mui/icons-material/CloseRounded";
import HelpOutlineRounded from "@mui/icons-material/HelpOutlineRounded";
import SmartToyOutlined from "@mui/icons-material/SmartToyOutlined";
import PaymentsOutlined from "@mui/icons-material/PaymentsOutlined";
import GraphicEqRounded from "@mui/icons-material/GraphicEqRounded";

const icons = {
  bot: SmartToyOutlined,
  money: PaymentsOutlined,
  waveform: GraphicEqRounded,
  explore: ExploreOutlined,
  plus: AddRounded,
  panel: SpaceDashboardOutlined,
  chat: ChatBubbleOutlineRounded,
  pin: PlaceOutlined,
  cloud: CloudOutlined,
  food: RestaurantOutlined,
  museum: AccountBalanceOutlined,
  family: FamilyRestroomOutlined,
  speaker: VolumeUpOutlined,
  send: SendRounded,
  clock: ScheduleRounded,
  close: CloseRounded,
  help: HelpOutlineRounded,
};

export default function Icon({ name = "explore", size = 20 }) {
  const Component = icons[name] || icons.explore;
  return <Component aria-hidden="true" sx={{ fontSize: size }} />;
}
