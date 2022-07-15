import { createContext } from "react";

import { SimulationContext } from "./types";

export const SimulationReactContext = createContext<SimulationContext>({
  address: "",
  startDate: new Date(),
  today: new Date(),
});
