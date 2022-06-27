import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartData,
  DatasetChartOptions,
} from "chart.js";
import { deltaDate } from "../dateUtils";
import { useContext } from "react";
import { SimulationReactContext } from "../simulationContext";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const TREASURIES: Record<string, string> = {
  "0x1a9c8182c09f50c8318d769245bea52c32be35bc": "Uniswap",
  "0x660F6D6c9BCD08b86B50e8e53B537F2B40f243Bd": "FWB",
  "0x78605df79524164911c144801f41e9811b7db73d": "BitDAO",
  "0x0BC3807Ec262cB779b38D65b38158acC3bfedE10": "NounsDAO",
  "0x57a8865cfb1ecef7253c27da6b4bc3daee5be518": "Gitcoin DAO",
  "0xde21f729137c5af1b01d73af1dc21effa2b8a0d6": "Gitcoin DAO",
  "0xfe89cc7abb2c4183683ab71653c4cdc9b02d44b7": "ENS DAO",
  "0x849d52316331967b6ff1198e5e32a0eb168d039d": "Gnosis DAO",
  "0x0da0c3e52c977ed3cbc641ff02dd271c3ed55afe": "Gnosis DAO",
  "0xec83f750adfe0e52a8b0dba6eeb6be5ba0bee535": "Gnosis DAO",
  "0x54396b93c10c685a21c8b5610c15f82a54c9c22e": "Gnosis DAO",
};

type DateOption = {
  optionStartDate: Date;
  callback: () => void;
  unselectedText: string;
  selectedText: string;
};

export default function Chart({
  chartData,
  dateOptions,
}: {
  chartData: ChartData<"line">;
  dateOptions: DateOption[];
}) {
  const { address, startDate } = useContext(SimulationReactContext);
  return (
    <div className="w-full p-4">
      <Line
        data={chartData}
        options={{
          responsive: true,
          plugins: {
            legend: {
              position: "top" as const,
            },
            title: {
              display: true,
              text:
                address in TREASURIES
                  ? `${TREASURIES[address]} treasury`
                  : "Treasury holdings",
            },
          },
          elements: {
            point: {
              radius: 1,
            },
          },
        }}
      />
      <div className="m-4 flex space-x-0.5 items-center justify-center text-gray-700 text-s drop-shadow-lg">
        {dateOptions.map(
          ({ optionStartDate, callback, selectedText, unselectedText }) => (
            <div
              key={optionStartDate.toString()}
              className={`hover:cursor-pointer p-2  ${
                startDate.getTime() === optionStartDate.getTime()
                  ? "bg-strawberry font-bold text-[#fff]"
                  : "bg-[#fff] font-semibold"
              }`}
              onClick={callback}
            >
              {startDate.getTime() === optionStartDate.getTime()
                ? selectedText
                : unselectedText}
            </div>
          )
        )}
      </div>
    </div>
  );
}
