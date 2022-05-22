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

type ProductDescription = {
  name: string;
  provider: string;
  description: string;
  tokens: string[];
  logo: string;
};
type AssetsBreakdown = Record<
  string,
  {
    allocation: number;
    volatility: number;
    riskContribution: number;
  }
>;
type Kpis = {
  "total value"?: number;
  volatility?: number;
  "return vs market"?: number | "Infinity";
};

const getTodayMidnight = () => {
  const today = new Date();
  today.setUTCHours(0, 0, 0, 0);
  return today;
};

// https://stackoverflow.com/a/54452875/931156
function deltaDate(input: Date, years: number, months: number, days: number) {
  return new Date(
    input.getFullYear() + years,
    input.getMonth() + months,
    Math.min(
      input.getDate() + days,
      new Date(
        input.getFullYear() + years,
        input.getMonth() + months + 1,
        0
      ).getDate()
    )
  );
}

function App() {
  const today = getTodayMidnight();

  const [address, setAddress] = useState("");
  const [startDate, setStartDate] = useState(deltaDate(today, -1, 0, 0));
  const [baseKpis, setBaseKpis] = useState({
    "total value": undefined,
    volatility: undefined,
    "return vs market": undefined,
  } as Kpis);
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
  const [activeProduct, setActiveProduct] = useState<undefined | number>();

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

  // Fetch product endpoint
  useEffect(() => {
    (async () => {
      if (typeof activeProduct === "undefined") return;
      setNewKpis({
        "total value": 1_548_000_000,
        volatility: 0.03,
        "return vs market": 0.24,
      });
      setNewAssets({
        BIT: {
          allocation: 0.36,
          volatility: 0.03,
          riskContribution: 0.501,
        },
        ETH: {
          allocation: 0.208,
          volatility: 0.035,
          riskContribution: 0.03,
        },
        USDT: {
          allocation: 0.088,
          volatility: 0.001,
          riskContribution: -0.0002,
        },
        USDC: {
          allocation: 0.31,
          volatility: 0.001,
          riskContribution: -0.0006,
        },
        "FTX Token": {
          allocation: 0.056,
          volatility: 0.035,
          riskContribution: 0.0624,
        },
      });
      setChartData({
        labels: chartData.labels,
        datasets: [
          chartData.datasets[0],
          {
            label: "Diversified portfolio",
            backgroundColor: "rgb(213, 175, 8)",
            borderColor: "rgb(213, 175, 8)",
            data: [
              452.6941098934827, 463.6397946467189, 455.5047562496766,
              456.36132148727495, 483.6656955092756, 484.9533924145435,
              460.89433491398825, 506.5431325131194, 514.5971520018533,
              510.59052975170994, 493.67231660521475, 459.3410708848855,
              467.5244544923157, 449.68820642502055, 440.3114325391505,
              452.84914505971454, 476.8506904269969, 458.32496670414196,
              450.56138112322526, 453.64571630065296, 443.64083710832807,
              455.08609547672586, 459.8235841115545, 483.67633563662196,
              491.36522529599995, 561.65707676286, 562.5500700221238,
              548.1715154589527, 553.968306353087, 566.4439394541043,
              574.8829178365849, 590.3442684709377, 588.665408376322,
              594.4673428696434, 619.0416780102829, 629.0867835055795,
              637.2925831732117, 635.7998699349092, 619.4509168253362,
              645.2833166761053, 646.335970922155, 659.610535646079,
              659.8338889711418, 643.3127676075294, 601.59393040814,
              611.9309690628705, 602.8483128737323, 616.0325328932566,
              608.1703957494192, 569.2429110552254, 576.3080849549804,
              592.2335176250816, 574.9351234575005, 577.8347491447983,
              583.4674918476527, 570.4244312699586, 581.9615365931364,
              650.8565078069246, 647.2260350186024, 629.7402284805164,
              626.1167682137842, 621.2110373014021, 619.5665201890761,
              634.9260825013306, 597.368114331222, 612.7894662021478,
              620.6682448465982, 600.1960986501654, 585.5681134260443,
              602.9792026757395, 602.8648287660592, 588.8366996603888,
              616.0351931156639, 582.077991061278, 554.0168172544792,
              545.2671576806856, 524.9222834778254, 477.53929054443535,
              494.33879488567453, 445.27854202237546, 428.812263974043,
              436.8322357258108, 445.9312017592745, 460.1010014105559,
              439.77063661518514, 452.49722622307354, 420.8209018193212,
              471.75261120821017, 462.06552357328076,
            ],
          },
        ],
      });
    })();
  }, [activeProduct]);

  const resetAssets = () => {
    setNewKpis(undefined);
    setNewAssets(undefined);
    setChartData({
      labels: chartData.labels,
      datasets: [chartData.datasets[0]],
    });
  };

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
          <div className="w-full bg-[#ddd] p-4 text-white  ">
            <div className="flex items-center justify-center">
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
            <div className="m-4 space-x-0.5 flex items-center justify-center text-gray-700 text-xs">
              <div
                className={`hover:cursor-pointer p-2 ${
                  startDate.getTime() === deltaDate(today, -1, 0, 0).getTime()
                    ? "bg-[#d5af08b8] font-semibold"
                    : "bg-white"
                }`}
                onClick={(el) => {
                  setStartDate(deltaDate(today, -1, 0, 0));
                }}
              >
                1 year
              </div>
              <div
                className={`hover:cursor-pointer p-2 ${
                  startDate.getTime() === deltaDate(today, 0, -3, 0).getTime()
                    ? "bg-[#d5af08b8] font-semibold"
                    : "bg-white"
                }`}
                onClick={() => {
                  setStartDate(deltaDate(today, 0, -3, 0));
                }}
              >
                3 months
              </div>
              <div
                className={`hover:cursor-pointer p-2 ${
                  startDate.getTime() === deltaDate(today, 0, -1, 0).getTime()
                    ? "bg-[#d5af08b8] font-semibold"
                    : "bg-white"
                }`}
                onClick={() => {
                  setStartDate(deltaDate(today, 0, -1, 0));
                }}
              >
                1 month
              </div>
            </div>
          </div>
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
          {products.map((props, index) =>
            openedProduct === undefined ? (
              <Product
                key={index}
                opened={false}
                {...props}
                toggle={() => setOpenedProduct(index)}
              />
            ) : (
              index === openedProduct && (
                <Product
                  key={index}
                  opened={true}
                  {...props}
                  toggle={() => setOpenedProduct(undefined)}
                  updatePreview={() => setActiveProduct(index)}
                  resetPreview={() => resetAssets()}
                />
              )
            )
          )}
        </div>
      </div>
    </div>
  );
}

function KpisDisplay({
  newKpis,
  baseKpis,
}: {
  newKpis: Kpis | undefined;
  baseKpis: Kpis;
}) {
  const kpis = newKpis || baseKpis;
  return (
    <div className="mb-10 flex justify-between items-center">
      <div className="bg-[#ddd] w-40 pb-4 pt-4 pl-6 pr-6 text-center">
        <p
          className={
            (newKpis === undefined ? "" : "text-[#D5AF08] ") +
            "text-2xl font-bold"
          }
        >
          {typeof kpis["total value"] !== "undefined" &&
            "$" + (kpis["total value"] / 1_000_000).toFixed(0) + "m"}
        </p>
        <p>Total Value</p>
      </div>{" "}
      <div className="bg-[#ddd] w-40 pb-4 pt-4 pl-6 pr-6 text-center">
        <p
          className={
            (newKpis === undefined ? "" : "text-[#D5AF08] ") +
            "text-2xl font-bold"
          }
        >
          {typeof kpis.volatility !== "undefined" &&
            (kpis.volatility * 100).toFixed(0) + "%"}
        </p>
        <p>Volatility</p>
      </div>
      <div className="bg-[#ddd] w-40 pb-4 pt-4 pl-6 pr-6 text-center">
        <p
          className={
            (newKpis === undefined ? "" : "text-[#D5AF08] ") +
            "text-2xl font-bold"
          }
        >
          {typeof kpis["return vs market"] !== "undefined" &&
            (kpis["return vs market"] === "Infinity"
              ? "∞"
              : ((kpis["return vs market"] as number) * 100).toFixed(0) + "%")}
        </p>
        <p>Return vs ETH</p>
      </div>
    </div>
  );
}

function AssetsDisplay({
  newAssets,
  baseAssets,
}: {
  newAssets: AssetsBreakdown | undefined;
  baseAssets: AssetsBreakdown;
}) {
  const assets = newAssets || baseAssets;
  const introducedAssetsNames =
    newAssets === undefined
      ? []
      : Object.keys(newAssets).filter(
          (assetName) => !Object.keys(baseAssets).includes(assetName)
        );

  return (
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
          ([assetName, { allocation, volatility, riskContribution }]) => (
            <tr key={assetName} className="border-b">
              <td className="p-2">
                <span
                  className={
                    (introducedAssetsNames.includes(assetName)
                      ? "text-[#D5AF08] "
                      : "text-[#666] ") + "text-l mr-2"
                  }
                >
                  ●
                </span>
                {assetName}
              </td>
              <td className="p-2">{`${(allocation * 100).toFixed(0)}%`}</td>
              <td className="p-2">{`${(volatility * 100).toFixed(1)}%`}</td>
              <td className="p-2">{`${(riskContribution * 100).toFixed(
                2
              )}%`}</td>
            </tr>
          )
        )}
      </tbody>
    </table>
  );
}

function Product({
  name,
  provider,
  description,
  tokens,
  opened,
  toggle,
  updatePreview,
  resetPreview,
}: ProductDescription & {
  opened: boolean;
  toggle: () => void;
  updatePreview?: () => void;
  resetPreview?: () => void;
}) {
  return (
    <div>
      <div
        className={
          (opened ? "" : "hover:cursor-pointer hover:bg-[#ccc] ") +
          "p-4 bg-[#ddd] flex items-center justify-between"
        }
        onClick={toggle}
      >
        <div className="flex items-center justify-start">
          <img src={logo} className="h-20" />
          <div className="ml-4">
            <div className="text-2xl">{name}</div>
            <div className="uppercase text-sm">
              <b>{provider}</b> · {description}
            </div>
            <div>
              {tokens.map((token) => (
                <span
                  key={token}
                  className="bg-[#bbb] pl-1 pr-1 p-0.5 rounded-2xl text-xs"
                >
                  {token}
                </span>
              ))}
            </div>
          </div>
        </div>
        <span
          className={
            (opened ? "" : "invisible ") +
            "hover:cursor-pointer hover:bg-[#ccc] text-right text-2xl mb-12 px-2 rounded-2xl"
          }
          onClick={resetPreview}
        >
          𝗫
        </span>
      </div>
      {opened && (
        <div className="p-4 space-y-2 text-xl font-semibold">
          <div className="p-4 space-y-2">
            <h3 className="font-bold">You swap</h3>
            <div className="flex items-center justify-between">
              <span className="uppercase">Asset</span>
              <span>
                <input className="w-[3em] p-2 text-right" placeholder="20%" />
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="uppercase">Value</span>
              <span>
                <input
                  className="p-2 text-right"
                  disabled={true}
                  value={"$12,000,000"}
                />
              </span>
            </div>
          </div>
          <div className="p-4 space-y-2 bg-[#ddd]">
            <h3 className="font-bold">You receive</h3>
            <div className="flex items-center justify-between">
              <span className="uppercase">UDSC</span>
              <span>
                <input
                  className="p-2 text-right bg-[#ddd]"
                  disabled={true}
                  value={"20,000"}
                />
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="uppercase">Value</span>
              <span>
                <input
                  className="p-2 text-right bg-[#ddd]"
                  disabled={true}
                  value={"$12,000,000"}
                />
              </span>
            </div>
          </div>
          <div className="pt-8 flex items-center justify-center">
            <button
              className=" py-4 px-8 bg-[#D5AF08] hover:bg-[#444] text-white font-bold"
              onClick={updatePreview}
            >
              Review order
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
