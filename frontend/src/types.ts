export type AssetsBreakdown = Record<
  string,
  {
    allocation: number;
    volatility: number;
    riskContribution: number;
  }
>;
export type Kpis = {
  totalValue: number;
  volatility: number;
  returnVsMarket: number | "Infinity";
};

export type SimulationContext = {
  address: string;
  startDate: Date;
  today: Date;
};
