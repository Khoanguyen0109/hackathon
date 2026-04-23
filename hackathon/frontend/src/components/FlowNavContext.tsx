import { createContext, useContext, useState, useCallback, useMemo } from "react";
import type { ReactNode } from "react";

interface FlowNavOverride {
  nextDisabled?: boolean;
  nextLabel?: string;
  nextVariant?: "primary" | "success";
  onNext?: () => void;
}

interface FlowNavContextValue {
  override: FlowNavOverride;
  setOverride: (o: FlowNavOverride) => void;
  clearOverride: () => void;
}

const Ctx = createContext<FlowNavContextValue>({
  override: {},
  setOverride: () => {},
  clearOverride: () => {},
});

export function FlowNavProvider({ children }: { children: ReactNode }) {
  const [override, setOverrideState] = useState<FlowNavOverride>({});

  const setOverride = useCallback((o: FlowNavOverride) => setOverrideState(o), []);
  const clearOverride = useCallback(() => setOverrideState({}), []);

  const value = useMemo(
    () => ({ override, setOverride, clearOverride }),
    [override, setOverride, clearOverride],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useFlowNavOverride() {
  return useContext(Ctx);
}
