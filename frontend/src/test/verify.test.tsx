import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AccessCodePage from "@/app/patient/verify/page";
import { LanguageProvider } from "@/lib/context/LanguageContext";

function renderWithContext(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe("AccessCodePage", () => {
  it("renders input field and remaining attempts counter", () => {
    renderWithContext(<AccessCodePage />);

    expect(screen.getByText("Enter Access Code")).toBeInTheDocument();
    expect(screen.getByLabelText(/Printed Access Code/i)).toBeInTheDocument();
    expect(screen.getByText(/3 attempts remaining before temporary lock/i)).toBeInTheDocument();
    expect(screen.getByText("Verify Code")).toBeInTheDocument();
  });

  it("decrements remaining attempts on invalid code entry", async () => {
    renderWithContext(<AccessCodePage />);

    const input = screen.getByLabelText(/Printed Access Code/i);
    fireEvent.change(input, { target: { value: "WRONG1" } });

    const submitBtn = screen.getByText("Verify Code");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Invalid code/i)).toBeInTheDocument();
      expect(screen.getByText(/2 attempts remaining before temporary lock/i)).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it("displays expired code state for EXPIRED", async () => {
    renderWithContext(<AccessCodePage />);

    const input = screen.getByLabelText(/Printed Access Code/i);
    fireEvent.change(input, { target: { value: "EXPIRED" } });

    const submitBtn = screen.getByText("Verify Code");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Access Code Expired")).toBeInTheDocument();
      expect(screen.getByText(/This access code has expired/i)).toBeInTheDocument();
    }, { timeout: 2000 });
  });
});
