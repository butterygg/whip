import { AssetsBreakdown } from "../types";

export default function AssetsDisplay({
  newAssets,
  baseAssets,
  selectedAsset,
}: {
  newAssets: AssetsBreakdown | undefined;
  baseAssets: AssetsBreakdown;
  selectedAsset: string | undefined;
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
                (selectedAsset === assetName ? "font-extrabold " : "") +
                "border-b"
              }
            >
              <td className="p-2">
                <span
                  className={
                    (assetName === selectedAsset
                      ? "text-strawberry "
                      : "text-[#000] text-opacity-50 ") + " text-l mr-2"
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
