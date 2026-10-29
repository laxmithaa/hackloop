import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import IdentifyPage from "@/app/patient/identify/page";
import { LanguageProvider } from "@/lib/context/LanguageContext";

function renderWithContext(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe("IdentifyPage", () => {
  it("renders both Option A (Upload) and Option B (Bill Number)", () => {
    renderWithContext(<IdentifyPage />);

    expect(screen.getByText(/Option B: Enter Bill Number/i)).toBeInTheDocument();
    expect(screen.getByText(/Option A: Upload Bill Photo/i)).toBeInTheDocument();
    expect(screen.getByText(/Low-Bandwidth Mode/i)).toBeInTheDocument();
  });

  it("validates empty or invalid bill number", async () => {
    renderWithContext(<IdentifyPage />);

    const input = screen.getByLabelText(/Hospital Bill Number/i);
    fireEvent.change(input, { target: { value: "ab" } });

    const submitBtn = screen.getByRole("button", { name: /Find Bill/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Bill number must be at least 3 characters/i)).toBeInTheDocument();
    });
  });

  it("displays verification required state for BILL-2026-001", async () => {
    renderWithContext(<IdentifyPage />);

    const input = screen.getByLabelText(/Hospital Bill Number/i);
    fireEvent.change(input, { target: { value: "BILL-2026-001" } });

    const submitBtn = screen.getByRole("button", { name: /Find Bill/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Additional Verification Required")).toBeInTheDocument();
      expect(screen.getByText("Enter Access Code")).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it("displays not found state for NOTFOUND-99", async () => {
    renderWithContext(<IdentifyPage />);

    const input = screen.getByLabelText(/Hospital Bill Number/i);
    fireEvent.change(input, { target: { value: "NOTFOUND-99" } });

    const submitBtn = screen.getByRole("button", { name: /Find Bill/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Bill Not Found")).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it("displays unregistered hospital state for UNREG-770", async () => {
    renderWithContext(<IdentifyPage />);

    const input = screen.getByLabelText(/Hospital Bill Number/i);
    fireEvent.change(input, { target: { value: "UNREG-770" } });

    const submitBtn = screen.getByRole("button", { name: /Find Bill/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Hospital Not Registered")).toBeInTheDocument();
    }, { timeout: 2000 });
  });
});
