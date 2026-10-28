import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import BillInformationPage from "@/app/patient/bill/page";
import { LanguageProvider } from "@/lib/context/LanguageContext";

function renderWithContext(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe("BillInformationPage", () => {
  it("renders verified bill information with 4 clear financial breakdowns", () => {
    renderWithContext(<BillInformationPage />);

    expect(screen.getByText("Sunrise Community Hospital")).toBeInTheDocument();
    expect(screen.getByText("BILL-2026-001")).toBeInTheDocument();
    expect(screen.getByText(/Total Hospital Charges/i)).toBeInTheDocument();
    expect(screen.getByText(/Covered by Insurance/i)).toBeInTheDocument();
    expect(screen.getByText(/Amount Already Deposited/i)).toBeInTheDocument();
    expect(screen.getByText(/Amount Payable by Patient/i)).toBeInTheDocument();
  });

  it("shows amount discrepancy notice when discrepancy preset is selected", () => {
    renderWithContext(<BillInformationPage />);

    const discrepancyBtn = screen.getByRole("button", { name: /Discrepancy Detected/i });
    fireEvent.click(discrepancyBtn);

    expect(screen.getByText("Amount Discrepancy Flagged")).toBeInTheDocument();
    expect(screen.getByText("Discrepancy Notice Detected")).toBeInTheDocument();
  });
});
