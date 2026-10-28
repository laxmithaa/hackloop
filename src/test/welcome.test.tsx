import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import WelcomePage from "@/app/page";
import { LanguageProvider } from "@/lib/context/LanguageContext";

function renderWithContext(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe("WelcomePage", () => {
  it("renders application name and primary CTA button", () => {
    renderWithContext(<WelcomePage />);

    expect(screen.getAllByText(/Healthcare/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Understand My Hospital Bill")).toBeInTheDocument();
    expect(screen.getByText("Caregiver Summary")).toBeInTheDocument();
  });

  it("renders official notice and medical disclaimer", () => {
    renderWithContext(<WelcomePage />);

    expect(screen.getByText(/does not replace the hospital's official paper bill/i)).toBeInTheDocument();
  });

  it("allows switching language to Hindi and Kannada", () => {
    renderWithContext(<WelcomePage />);

    const hindiBtn = screen.getByRole("button", { name: "हिंदी (Hindi)" });
    fireEvent.click(hindiBtn);

    expect(screen.getByText("अपना अस्पताल बिल समझें")).toBeInTheDocument();

    const kannadaBtn = screen.getByRole("button", { name: "ಕನ್ನಡ (Kannada)" });
    fireEvent.click(kannadaBtn);

    expect(screen.getByText("ನನ್ನ ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ")).toBeInTheDocument();
  });
});
