import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import LandingPage from "../LandingPage";
import * as client from "../../api/client";

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe("LandingPage integration", () => {
  it("renders hero, inputs, and project list section", async () => {
    vi.spyOn(client, "listProjects").mockResolvedValue({ projects: [] });
    render(<LandingPage />, { wrapper: Wrapper });
    expect(screen.getByText(/Code Graph/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/github\.com/i)).toBeInTheDocument();
    expect(screen.getByText(/Drop a .zip/i)).toBeInTheDocument();
    await screen.findByText(/No indexed projects yet/i);
  });
});
