import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import GitHubInput from "../GitHubInput";
import * as client from "../../../api/client";

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe("GitHubInput", () => {
  it("disables submit for invalid URL", () => {
    render(<GitHubInput />, { wrapper: Wrapper });
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
  });

  it("enables submit for valid GitHub URL", () => {
    render(<GitHubInput />, { wrapper: Wrapper });
    const input = screen.getByPlaceholderText(/github\.com/i);
    fireEvent.change(input, {
      target: { value: "https://github.com/owner/repo" },
    });
    expect(screen.getByRole("button")).not.toBeDisabled();
  });

  it("shows error on API failure", async () => {
    vi.spyOn(client, "createProjectFromGitHub").mockRejectedValueOnce(
      new Error("Network error")
    );
    render(<GitHubInput />, { wrapper: Wrapper });
    const input = screen.getByPlaceholderText(/github\.com/i);
    fireEvent.change(input, {
      target: { value: "https://github.com/owner/repo" },
    });
    fireEvent.submit(screen.getByRole("button").closest("form")!);
    await waitFor(() =>
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    );
  });
});
