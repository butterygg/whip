import { useState, useContext } from "react";
import { SimulationReactContext } from "../simulationContext";
import { Kpis, AssetsBreakdown } from "../types";
import logo from "../whipped-cream.png";

type ProductDescription = {
  name: string;
  provider: string;
  description: string;
  tokens: string[];
  logo: string;
};

export default function Product({
  name,
  provider,
  description,
  tokens,
  assets,
  selectedAsset,
  setSelectedAsset,
  swappedAmount,
  opened,
  previewIsOn,
  toggle,
  previewNewKpis,
  previewNewAssets,
  previewNewChartData,
  resetPreview,
}: ProductDescription & {
  assets: string[];
  selectedAsset: string | undefined;
  setSelectedAsset: (arg0: string | undefined) => void;
  swappedAmount: number | undefined;
  opened: boolean;
  previewIsOn: boolean;
  toggle: () => void;
  previewNewKpis: (arg0: Kpis) => void;
  previewNewAssets: (arg0: AssetsBreakdown) => void;
  previewNewChartData: (arg0: Record<string, number>) => void;
  resetPreview: () => void;
}) {
  const [percentage, setPercentage] = useState(20);
  const { address, startDate } = useContext(SimulationReactContext);

  // Fetch product endpoint
  const launchPreview = async () => {
    if (!opened) return;

    const resp = await fetch(
      `/api/backtest/spread/${address}/${startDate
        .toISOString()
        .slice(0, 10)}/${selectedAsset}/USDC/${percentage}`
    );
    if (!resp.ok)
      throw new Error(`Backtest fetch failed with status: ${resp.statusText}`);
    const { assets, kpis, data } = await resp.json();

    previewNewKpis(kpis);
    previewNewAssets(assets);
    previewNewChartData(data);
  };

  return (
    <div>
      <div
        className={
          (opened
            ? "bg-biscuit bg-opacity-90 "
            : "bg-biscuit hover:cursor-pointer hover:bg-[#ccc] rounded-lg ") +
          "p-4 text-[#fff] flex items-center justify-between"
        }
        onClick={toggle}
      >
        <div className="flex items-center justify-start">
          <img src={logo} className="h-20" />
          <div className="ml-4">
            <div className="text-2xl">{name}</div>
            <div className="uppercase text-xs">
              <b>{provider}</b> · {description}
            </div>
            <div>
              {tokens.map((token) => (
                <span
                  key={token}
                  className="border-[1px] border-[#fff] pl-1 pr-1 p-0.5 rounded-2xl text-xs"
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
            "hover:cursor-pointer hover:text-strawberry text-right text-2xl mb-12 px-2 rounded-2xl"
          }
          onClick={resetPreview}
        >
          𝗫
        </span>
      </div>
      {opened && (
        <div className="p-4 space-y-2 text-xl font-semibold bg-biscuit bg-opacity-20">
          <div className="p-4 space-y-2">
            <h3 className="font-light">You swap</h3>
            <div className="flex items-center justify-between text-l">
              <span>
                <select
                  onChange={(event) => setSelectedAsset(event.target.value)}
                  className="bg-biscuit bg-opacity-10 border-strawberry border-2 font-bold"
                >
                  <option value="">select an asset</option>
                  {assets.map((asset) => (
                    <option
                      key={asset}
                      value={asset}
                      selected={asset === selectedAsset}
                    >
                      {asset}
                    </option>
                  ))}
                </select>
              </span>
              <span className="relative">
                <input
                  className="bg-biscuit bg-opacity-10 border-strawberry border-2 w-[5em] p-2 pr-5 text-right font-bold"
                  placeholder="20"
                  type="number"
                  min="0"
                  max="100"
                  onChange={(e) => setPercentage(parseInt(e.target.value))}
                  value={percentage}
                />
                <span className="absolute right-2 h-[100%] top-0 flex items-center">
                  <p className="text-sm">%</p>
                </span>
              </span>
            </div>
            {/* <div className="flex items-center justify-between">
              <span className="uppercase">Value</span>
              <span className="flex items-center justify-between space-x-2">
                <span>$12,000,000</span>
              </span>
            </div> */}
          </div>
          {swappedAmount !== undefined && (
            <div className="bg-custard rounded-lg p-4 space-y-2">
              <h3 className="font-light">You receive</h3>
              <div className="flex items-center justify-between">
                <span className="uppercase">UDSC</span>
                <span>
                  <input
                    className="bg-custard p-2 text-right"
                    disabled={true}
                    value={"20,000"}
                  />
                </span>
              </div>
              {/* <div className="flex items-center justify-between">
              <span className="uppercase">Value{"\u00A0"}$</span>
              <span>
                <input
                  className="p-2 text-right bg-[#ddd]"
                  disabled={true}
                  value={"$12,000,000"}
                />
              </span>
            </div> */}
            </div>
          )}
          <div className="p-4 space-y-2">
            <div className="pt-8 flex items-center justify-center space-x-6">
              {previewIsOn && (
                <button
                  className="bg-biscuit hover:bg-opacity-50 py-4 px-8 text-[#fff] font-bold"
                  onClick={() => {
                    resetPreview();
                    setSelectedAsset(undefined);
                  }}
                >
                  Clear
                </button>
              )}
              {selectedAsset ? (
                <button
                  className="bg-strawberry hover:bg-opacity-50 py-4 px-8 text-[#fff] font-bold"
                  onClick={() => {
                    resetPreview();
                    selectedAsset && launchPreview();
                  }}
                >
                  {previewIsOn ? "Update" : "Preview"}
                </button>
              ) : (
                <button
                  className="bg-strawberry bg-opacity-10 py-4 px-8 text-[#666] font-bold"
                  disabled={true}
                >
                  {previewIsOn ? "Update" : "Preview"}
                </button>
              )}
            </div>
            <div
              className={
                "pt-1 space-y-2 text-sm text-center" +
                (selectedAsset ? " invisible" : "")
              }
            >
              <em>To run a preview, first select an asset to be spread.</em>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
