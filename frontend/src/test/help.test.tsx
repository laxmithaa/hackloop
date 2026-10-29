import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import HumanSupportPage from "@/app/patient/help/page";
import { LanguageProvider } from "@/lib/context/LanguageContext";

function renderWithContext(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe("HumanSupportPage", () => {
  it("renders form fields, callback times, and consent checkbox", () => {
    renderWithContext(<HumanSupportPage />);

    expect(screen.getByText("Request Human Assistance")).toBeInTheDocument();
    expect(screen.getByLabelText(/Your Name/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue("+91 98765 43210")).toBeInTheDocument();
    expect(screen.getByText(/Preferred Callback Time/i)).toBeInTheDocument();
    expect(screen.getByText(/I explicitly consent to sharing this bill reference/i)).toBeInTheDocument();
  });

  it("validates missing consent before submission", async () => {
    renderWithContext(<HumanSupportPage />);

    const submitBtn = screen.getByRole("button", { name: /Submit Support Request/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/You must provide consent for a worker to call you/i)).toBeInTheDocument();
    });
  });

  it("successfully submits demonstration request and presents reference ID", async () => {
    renderWithContext(<HumanSupportPage />);

    const consentBox = screen.getByRole("checkbox");
    fireEvent.click(consentBox);

    const submitBtn = screen.getByRole("button", { name: /Submit Support Request/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Support Request Received")).toBeInTheDocument();
      expect(screen.getByText(/Your Case Reference ID:/i)).toBeInTheDocument();
      expect(screen.getByText(/DEMO NOTICE: This is a demonstration interface/i)).toBeInTheDocument();
    }, { timeout: 2000 });
  });
});
