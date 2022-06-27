import { Kpis } from "../types";

export default function KpisDisplay({
  newKpis,
  baseKpis,
}: {
  newKpis: Kpis | undefined;
  baseKpis: Kpis | undefined;
}) {
  const kpis = newKpis || baseKpis;
  return (
    <div className="mb-10 flex justify-between items-center text-[#fff]">
      <div className="bg-biscuit rounded-lg w-40 pb-4 pt-4 pl-6 pr-6 text-center">
        {typeof kpis !== "undefined" && (
          <p
            className={
              (newKpis === undefined ? "" : "text-strawberry ") +
              "text-3xl font-bold"
            }
          >
            ${(kpis.totalValue / 1_000_000).toFixed(0)}m
          </p>
        )}
        <p>Total Value</p>
      </div>{" "}
      <div className="bg-biscuit rounded-lg w-40 pb-4 pt-4 pl-6 pr-6 text-center">
        {typeof kpis !== "undefined" && (
          <p
            className={
              (newKpis === undefined ? "" : "text-strawberry ") +
              "text-3xl font-bold"
            }
          >
            {(kpis.volatility * 100).toFixed(0)}%
          </p>
        )}
        <p>Volatility</p>
      </div>
      <div className="bg-biscuit rounded-lg w-40 pb-4 pt-4 pl-6 pr-6 text-center">
        {typeof kpis !== "undefined" && (
          <p
            className={
              (newKpis === undefined ? "" : "text-strawberry ") +
              "text-3xl font-bold"
            }
          >
            {kpis.returnVsMarket === "Infinity"
              ? "∞"
              : kpis.returnVsMarket > 100_000
              ? "💥"
              : ((kpis.returnVsMarket as number) * 100).toFixed(0) + "%"}
          </p>
        )}
        <p>Return vs ETH</p>
      </div>
    </div>
  );
}
