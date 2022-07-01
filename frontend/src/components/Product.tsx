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
  selectedAsset,
  opened,
  previewIsOn,
  toggle,
  previewNewKpis,
  previewNewAssets,
  previewNewChartData,
  resetPreview,
}: ProductDescription & {
  selectedAsset?: string | undefined;
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
        .slice(0, 10)}/${selectedAsset}/${percentage}`
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
          (opened ? "" : "hover:cursor-pointer hover:bg-[#ccc] ") +
          "p-4 bg-[#ddd] flex items-center justify-between"
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
              <span className="uppercase">Asset{"\u00A0"}%</span>
              <span>
                <input
                  className="w-[3em] p-2 text-right"
                  placeholder="20"
                  type="number"
                  min="0"
                  max="100"
                  onChange={(e) => setPercentage(parseInt(e.target.value))}
                  value={percentage}
                />
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="uppercase">Value{"\u00A0"}$</span>
              <span>
                <input
                  className="p-2 text-right"
                  disabled={true}
                  value="12,000,000"
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
              <span className="uppercase">Value{"\u00A0"}$</span>
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
            {previewIsOn ? (
              <button
                className="bg-[#666] hover:bg-[#444] py-4 px-8 text-white font-bold"
                onClick={() => resetPreview()}
              >
                Reset preview
              </button>
            ) : selectedAsset ? (
              <button
                className="bg-[#D5AF08] hover:bg-[#444] py-4 px-8 text-white font-bold"
                onClick={() => selectedAsset && launchPreview()}
              >
                Run preview
              </button>
            ) : (
              <button
                className="bg-[#eaeaea] py-4 px-8 text-[#666] font-bold"
                disabled={true}
              >
                Run preview
              </button>
            )}
          </div>
          <div
            className={
              "p-1 space-y-2 text-sm text-center" +
              (selectedAsset ? " invisible" : "")
            }
          >
            <p>To run the preview, first select an asset to be spread.</p>
          </div>
        </div>
      )}
    </div>
  );
}
