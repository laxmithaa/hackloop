import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ConsentPage from "@/app/patient/page";
import { LanguageProvider } from "@/lib/context/LanguageContext";

function renderWithContext(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe("ConsentPage", () => {
  it("renders plain-language explanation of what info is used and why", () => {
    renderWithContext(<ConsentPage />);

    expect(screen.getByText("Your Privacy & Consent")).toBeInTheDocument();
    expect(screen.getByText(/1\. What information is used/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Why this information is needed/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. How the application uses it/i)).toBeInTheDocument();
    expect(screen.getByText("I Agree & Continue")).toBeInTheDocument();
    expect(screen.getByText("I Decline")).toBeInTheDocument();
  });

  it("shows informative limitation message when user declines without implying consent", () => {
    renderWithContext(<ConsentPage />);

    const declineBtn = screen.getByText("I Decline");
    fireEvent.click(declineBtn);

    expect(screen.getByText("Consent Declined")).toBeInTheDocument();
    expect(screen.getByText(/You have chosen not to proceed with automated bill analysis/i)).toBeInTheDocument();
    expect(screen.getByText("Review Consent Again")).toBeInTheDocument();
  });
});
