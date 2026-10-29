import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SupportWorkerDashboard from "@/app/support/page";
import { LanguageProvider } from "@/lib/context/LanguageContext";

function renderWithContext(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe("SupportWorkerDashboard", () => {
  it("renders dashboard heading and Demo Data badge", () => {
    renderWithContext(<SupportWorkerDashboard />);

    expect(screen.getByText("Support-Worker Dashboard")).toBeInTheDocument();
    expect(screen.getByText(/Demo Data · Simulated Staff Access/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Sunrise Community Hospital/i).length).toBeGreaterThan(0);
  });

  it("filters tickets by status", () => {
    renderWithContext(<SupportWorkerDashboard />);

    const resolvedBtns = screen.getAllByRole("button", { name: "Resolved" });
    fireEvent.click(resolvedBtns[0]);

    expect(screen.getByText("Basavaraj Patil")).toBeInTheDocument();
  });

  it("allows updating ticket status", () => {
    renderWithContext(<SupportWorkerDashboard />);

    const callbackBtn = screen.getAllByRole("button", { name: "Callback scheduled" });
    // Click the status update button in the right details panel
    fireEvent.click(callbackBtn[callbackBtn.length - 1]);

    expect(screen.getByText(/Status updated to "Callback scheduled"/i)).toBeInTheDocument();
  });
});
