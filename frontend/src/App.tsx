import { useEffect, useState } from "react";
import { ChartData } from "chart.js";

import logo from "./whipped-cream.png";
import "./App.css";
import { AssetsBreakdown, Kpis } from "./types";
import { getTodayMidnight, deltaDate } from "./dateUtils";
import { SimulationReactContext } from "./simulationContext";
import AssetsDisplay from "./components/AssetsDisplay";
import Product from "./components/Product";
import KpisDisplay from "./components/KpisDisplay";
import Chart from "./components/Chart";

const PRODUCTS = [
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

function App() {
  const today = getTodayMidnight();

  const [address, setAddress] = useState("");
  const [startDate, setStartDate] = useState(deltaDate(today, -1, 0, 0));
  const [baseKpis, setBaseKpis] = useState(undefined as Kpis | undefined);
  const [newKpis, setNewKpis] = useState(undefined as Kpis | undefined);
  const [baseAssets, setBaseAssets] = useState({} as AssetsBreakdown);
  const [newAssets, setNewAssets] = useState(
    undefined as AssetsBreakdown | undefined
  );

  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [],
  } as ChartData<"line">);
  const [openedProduct, setOpenedProduct] = useState<undefined | number>();

  // Change the URL
  useEffect(() => {
    if (typeof window !== "undefined") {
      if (address.length > 0)
        window.history.pushState(
          `Whip ${address.slice(0, 6)}`,
          `Whip ${address.slice(0, 6)}`,
          `${window.location.href.split("?")[0]}?${new URLSearchParams({
            address,
          }).toString()}`
        );
      else {
        const queryString = window.location.href.split("?")[1];
        if (queryString) {
          const params = new URLSearchParams(queryString);
          if (params.has("address")) {
            const param = params.get("address");
            if (typeof param === "string") setAddress(param);
          }
        }
      }
    }
  }, [address, setAddress]);

  // Fetch main endpoint
  useEffect(() => {
    (async () => {
      if (!address) return;
      const resp = await fetch(
        `/api/portfolio/${address}/${startDate.toISOString().slice(0, 10)}`
      );
      if (!resp.ok)
        throw new Error(
          `Portfolio fetch failed with status: ${resp.statusText}`
        );
      const { assets, kpis, data } = await resp.json();

      setBaseAssets(assets);
      setBaseKpis(kpis);

      setChartData({
        labels: Object.keys(data),
        datasets: [
          {
            label: "Total value in m USD",
            backgroundColor: "rgb(83, 83, 83)",
            borderColor: "rgb(83, 83, 83)",
            data: Object.values(data).map((x) => (x as number) / 1_000_000),
          },
        ],
      });
    })();
  }, [address, startDate]);

  const resetAssets = () => {
    setNewKpis(undefined);
    setNewAssets(undefined);
    setChartData({
      labels: chartData.labels,
      datasets: chartData.datasets.length === 0 ? [] : [chartData.datasets[0]],
    });
  };

  const previewNewChartData = (newData: Record<string, number>) => {
    setChartData({
      labels: chartData.labels,
      datasets: [
        chartData.datasets[0],
        {
          label: "Diversified portfolio",
          backgroundColor: "rgb(226, 97, 57)",
          borderColor: "rgb(226, 97, 57)",
          data: Object.values(newData).map((x) => (x as number) / 1_000_000),
        },
      ],
    });
  };

  const dateOptions = [
    {
      optionStartDate: deltaDate(today, -1, 0, 0),
      selectedText: "Past year",
      unselectedText: "1 year",
    },
    {
      optionStartDate: deltaDate(today, 0, -3, 0),
      selectedText: "Past 3 months",
      unselectedText: "3 months",
    },
    {
      optionStartDate: deltaDate(today, 0, -1, 0),
      selectedText: "Past month",
      unselectedText: "1 month",
    },
  ].map(({ optionStartDate, ...obj }) => ({
    optionStartDate: optionStartDate,
    callback: () => setStartDate(optionStartDate),
    ...obj,
  }));

  return (
    <SimulationReactContext.Provider
      value={{ address: address, startDate: startDate, today: today }}
    >
      <div>
        <header className="p-2 flex justify-between items-center">
          <div className="m-3 w-[28em] p-2"></div>
          <p className="text-6xl font-bold text-[#E1B76D]">WHIP</p>
          <input
            className="m-3 w-[28em] p-2"
            placeholder={address || "Address"}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                setAddress(event.currentTarget.value);
              }
            }}
          ></input>
        </header>
        <div className="flex items-center justify-center">
          <div className="w-2/3 m-10">
            <Chart chartData={chartData} dateOptions={dateOptions} />
            <div className="p-10">
              <KpisDisplay newKpis={newKpis} baseKpis={baseKpis} />
              <AssetsDisplay newAssets={newAssets} baseAssets={baseAssets} />
            </div>
          </div>
          <div
            className={
              (openedProduct === undefined ? "p-6 " : "") +
              "bg-[#eee] w-1/3 m-10 space-y-6"
            }
          >
            {openedProduct === undefined && (
              <h2 className="text-3xl mb-6">Products</h2>
            )}
            {PRODUCTS.map(
              (props, index) =>
                (openedProduct === undefined || index === openedProduct) && (
                  <Product
                    key={index}
                    opened={index === openedProduct}
                    toggle={() => {
                      if (index === 0 && typeof baseKpis !== "undefined")
                        setOpenedProduct(
                          index === openedProduct ? undefined : index
                        );
                    }}
                    previewNewKpis={setNewKpis}
                    previewNewAssets={setNewAssets}
                    previewNewChartData={previewNewChartData}
                    resetPreview={() => resetAssets()}
                    {...props}
                  />
                )
            )}
          </div>
        </div>
      </div>
    </SimulationReactContext.Provider>
  );
}

export default App;
