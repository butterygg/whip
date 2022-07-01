import { AssetsBreakdown } from "../types";

export default function AssetsDisplay({
  newAssets,
  baseAssets,
  assetsAreSelectable = false,
  selectedAsset,
  setSelectedAsset,
}: {
  newAssets: AssetsBreakdown | undefined;
  baseAssets: AssetsBreakdown;
  assetsAreSelectable?: boolean;
  selectedAsset: string | undefined;
  setSelectedAsset: (arg0: string | undefined) => void;
}) {
  const assets = newAssets || baseAssets;

  return (
    <table className="table-auto w-full text-left">
      <thead>
        <tr className="border-b-2 border-black">
          <th className="w-1/3 p-2">
            {" "}
            <span className="invisible text-l mr-2">●</span>Asset
          </th>
          <th className="p-2">Allocation</th>
          <th className="p-2">Volatility</th>
          <th className="p-2">Risk Contribution</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(assets).map(
          ([assetName, { allocation, volatility, riskContribution }]) => (
            <tr
              key={assetName}
              className={
                (assetsAreSelectable ? "hover:bg-white cursor-pointer " : "") +
                (selectedAsset === assetName ? "font-extrabold " : "") +
                "border-b"
              }
              onClick={() =>
                assetsAreSelectable &&
                setSelectedAsset(
                  assetName === selectedAsset ? undefined : assetName
                )
              }
            >
              <td className="p-2">
                <span
                  className={
                    (assetName === selectedAsset
                      ? "text-[#E26139] "
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
