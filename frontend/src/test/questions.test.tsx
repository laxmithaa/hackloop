import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import QuestionsPage from "@/app/patient/questions/page";
import { LanguageProvider } from "@/lib/context/LanguageContext";

function renderWithContext(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe("QuestionsPage", () => {
  it("renders sample questions, question input, and voice input controls", () => {
    renderWithContext(<QuestionsPage />);

    expect(screen.getByText("Ask Questions About Your Bill")).toBeInTheDocument();
    expect(screen.getByText(/What does General Consultation Fee mean\?/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Speak Question" })).toBeInTheDocument();
  });

  it("handles out-of-scope medical disease question with a clear refusal notice", async () => {
    renderWithContext(<QuestionsPage />);

    const input = screen.getByRole("textbox", { name: /Type or speak your question/i });
    fireEvent.change(input, { target: { value: "Can this medicine cure my cancer disease?" } });

    const submitBtn = screen.getByRole("button", { name: "Ask Question" });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Medical Scope Notice: I can only explain hospital billing terms/i)).toBeInTheDocument();
    }, { timeout: 2000 });
  });
});
