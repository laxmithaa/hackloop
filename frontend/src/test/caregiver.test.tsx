import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CaregiverSummaryPage from "@/app/caregiver/page";
import { LanguageProvider } from "@/lib/context/LanguageContext";

function renderWithContext(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe("CaregiverSummaryPage", () => {
  it("renders required heading 'What You Need to Know' and financial terms", () => {
    renderWithContext(<CaregiverSummaryPage />);

    expect(screen.getByText("What You Need to Know")).toBeInTheDocument();
    expect(screen.getByText(/Essential Bill Numbers/i)).toBeInTheDocument();
    expect(screen.getByText(/Important Terms on This Bill/i)).toBeInTheDocument();
    expect(screen.getByText(/Deadlines & Critical Dates/i)).toBeInTheDocument();
    expect(screen.getByText(/Questions to Ask the Hospital Billing Desk/i)).toBeInTheDocument();
    expect(screen.getByText(/Suggested Next Steps/i)).toBeInTheDocument();
  });
});
