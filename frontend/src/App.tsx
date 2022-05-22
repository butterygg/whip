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
        "total value": 1_433_489_765,
        volatility: 0.044,
        "return vs market": 0.18,
      });
      setNewAssets({
        UNI: {
          allocation: 0.8,
          volatility: 0.052,
          riskContribution: 1,
        },
        USDC: {
          allocation: 0.2,
          volatility: 0.0001,
          riskContribution: 0,
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
              501.07393327578797, 490.6410219873329, 526.116181498266,
              556.1416890647487, 548.251294489849, 535.2675166295701,
              514.0556126901168, 481.21387735414595, 491.28428090651,
              467.5892338269915, 461.11240474293504, 482.7718449901471,
              498.73311219808846, 476.1547586872153, 470.4765765726248,
              468.0430816211164, 454.98006017236213, 467.53563130749257,
              477.2648378101033, 494.1791636967664, 500.0377285818866,
              518.1742879375948, 520.4509949950595, 503.99443288253536,
              504.8270847150209, 522.7609328803725, 531.6231813700321,
              566.1493525054457, 559.2137360768705, 558.9690093241638,
              592.7064764180922, 572.6156743492405, 586.9227769180984,
              608.0778594315306, 583.9805943156259, 596.3367267194044,
              599.75112388648, 608.2987968142213, 594.3045721922251,
              577.4356304483623, 527.5236112948955, 551.1490636919361,
              516.4442175065085, 531.9634494858849, 525.0219721443382,
              485.2627255964389, 500.9157594378702, 515.1532813592157,
              507.0444838303761, 519.9932956507782, 515.6290050312157,
              497.09036273666374, 503.9365870505458, 509.67769550147807,
              499.95123859773327, 480.15228478549034, 482.7417093976729,
              483.2980097095981, 473.9123871048367, 475.61336248673024,
              443.03662635063324, 452.4372681800581, 450.3482925209935,
              427.6846285839989, 391.903127107845, 406.0846186391889,
              398.14439994229474, 394.5577618201554, 442.10384613494267,
              414.8892370147741, 427.58167047837554, 408.82704761155554,
              405.03686024343085, 358.89775797088123, 360.48968257303403,
              308.98050270014096, 301.13853977708015, 318.24262446730353,
              323.1975651311278, 455.5546491304233, 429.17778651931525,
              458.16388361772465, 419.10052553060063, 439.12421126277434,
              433.6958126589046,
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
