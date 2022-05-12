import { useEffect, useMemo, useState } from "react";
import { Line } from "react-chartjs-2";
import logo from "./whipped-cream.png";
import "./App.css";
import {
  Chart as ChartJS,
  ChartData,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

function App() {
  const [address, setAddress] = useState("");
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [],
  } as ChartData<"line">);

  const assets = {
    UNI: {
      allocation: 0.99,
      volatility: 0.7,
      riskContribution: 0.95,
    },
    DAI: {
      allocation: 0.01,
      volatility: 0.01,
      riskContribution: 0.01,
    },
  };

  const products = [
    {
      name: "Spread",
      provider: "Butter",
      description: "diversification · stables",
      tokens: ["USDC"],
      logo: logo,
    },
    {
      name: "Range Tokens",
      provider: "UMA",
      description: "debt-based funding",
      tokens: ["yUSD"],
      logo: logo,
    },
    {
      name: "Squeeth-Crab",
      provider: "Opyn",
      description: "hedging · eth",
      tokens: ["oSQTH"],
      logo: logo,
    },
    {
      name: "Spread",
      provider: "Butter",
      description: "diversification · ETH",
      tokens: ["ETH"],
      logo: logo,
    },
  ];

  useEffect(() => {
    // API call…
    setChartData({
      labels: ["January", "February", "March", "April", "May", "June"],
      datasets: [
        {
          label: "Total value in m USD",
          backgroundColor: "rgb(255, 99, 132)",
          borderColor: "rgb(255, 99, 132)",
          data: [42, 48, 45, 42, 33, 23],
        },
      ],
    });
  }, []);

  return (
    <div>
      <header className="p-2 bg-[#ddd] flex justify-between items-center">
        <div className="w-[15em]"></div>
        <img className="h-[100px]" src={logo} alt="logo" />
        <input
          className="m-3 w-[15em] p-2"
          placeholder={address || "Address"}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              setAddress(event.currentTarget.value);
            }
          }}
        ></input>
      </header>
      <div className="flex items-center justify-center">
        <div className="bg-[#eee] w-2/3 m-10">
          <div className="w-full bg-[#ddd] p-4 text-white  flex items-center justify-center">
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
                    text: "Treasury holdings",
                  },
                },
              }}
            />
          </div>
          <div className="p-10">
            <div className="mb-10 flex justify-between items-center">
              {Object.entries({
                "Total value": "$100m",
                Volatility: "High",
                "Return vs market": "11%",
              }).map(([type, value]) => (
                <div className="bg-[#ddd] w-40 pb-4 pt-4 pl-6 pr-6 text-center">
                  <p className="text-3xl bold">{value}</p>
                  <p className="text-sm">{type}</p>
                </div>
              ))}
            </div>
            <table className="table-auto w-full text-left">
              <thead>
                <tr className="border-b-2 border-black">
                  <th className="w-1/3 p-2">Asset</th>
                  <th className="p-2">Allocation</th>
                  <th className="p-2">Volatility</th>
                  <th className="p-2">Risk Contribution</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(assets).map(
                  ([
                    assetName,
                    { allocation, volatility, riskContribution },
                  ]) => (
                    <tr className="border-b">
                      <td className="p-2">{assetName}</td>
                      <td className="p-2">{`${allocation * 100}%`}</td>
                      <td className="p-2">{`${volatility}`}</td>
                      <td className="p-2">{`${riskContribution * 100}%`}</td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="bg-[#eee] w-1/3 m-10 p-6">
          <h2 className="text-3xl mb-6">Products</h2>
          {products.map(({ name, provider, description, tokens }) => (
            <div className="p-4 mt-6 bg-[#ddd] flex items-center justify-start">
              <img src={logo} className="h-20" />
              <div className="ml-4">
                <div className="text-2xl">{name}</div>
                <div className="uppercase text-sm">
                  <b>{provider}</b> · {description}
                </div>
                <div>
                  {tokens.map((token) => (
                    <span className="bg-[#bbb] pl-1 pr-1 p-0.5 rounded-2xl text-xs">
                      {token}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
