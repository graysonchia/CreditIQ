import { render, screen } from "@testing-library/react";
import { Users } from "lucide-react";
import { describe, expect, it } from "vitest";
import { StatCard } from "./StatCard";

describe("StatCard", () => {
  it("renders label, value, and detail", () => {
    render(<StatCard label="Total Customers" value="1K" detail="Active profiles" icon={Users} />);

    expect(screen.getByText("Total Customers")).toBeInTheDocument();
    expect(screen.getByText("1K")).toBeInTheDocument();
    expect(screen.getByText("Active profiles")).toBeInTheDocument();
  });
});
