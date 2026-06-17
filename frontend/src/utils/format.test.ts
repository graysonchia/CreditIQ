import { describe, expect, it } from "vitest";
import { riskLevel } from "./format";

describe("riskLevel", () => {
  it("classifies low, medium, and high risk scores", () => {
    expect(riskLevel(0.2)).toBe("Low");
    expect(riskLevel(0.5)).toBe("Medium");
    expect(riskLevel(0.8)).toBe("High");
  });
});
