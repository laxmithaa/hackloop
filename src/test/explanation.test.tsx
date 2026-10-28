import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ExplanationPage from "@/app/patient/explanation/page";
import { LanguageProvider } from "@/lib/context/LanguageContext";

function renderWithContext(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe("ExplanationPage", () => {
  it("renders heading and exact required information label", () => {
    renderWithContext(<ExplanationPage />);

    expect(screen.getByText("Understand Your Bill")).toBeInTheDocument();
    // REQUIRED EXACT LABEL
    expect(screen.getByText("Generated from hospital-provided bill information.")).toBeInTheDocument();
    expect(screen.getByText(/Listen Aloud/i)).toBeInTheDocument();
  });

  it("toggles simpler 5th-grade explanation version", () => {
    renderWithContext(<ExplanationPage />);

    const simplifyBtn = screen.getByRole("button", { name: /Make Explanation Simpler/i });
    fireEvent.click(simplifyBtn);

    expect(screen.getByText("Showing Simpler Version")).toBeInTheDocument();
    expect(screen.getByText(/Showing shorter, 5th-grade plain-language version/i)).toBeInTheDocument();
  });
});
