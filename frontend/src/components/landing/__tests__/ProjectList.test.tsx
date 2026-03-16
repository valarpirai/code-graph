import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import ProjectList from "../ProjectList";
import * as client from "../../../api/client";

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
);

describe("ProjectList", () => {
  it("shows empty state when no projects", async () => {
    vi.spyOn(client, "listProjects").mockResolvedValue({ projects: [] });
    render(<ProjectList />, { wrapper: Wrapper });
    await screen.findByText(/No indexed projects yet/i);
  });

  it("renders project names", async () => {
    vi.spyOn(client, "listProjects").mockResolvedValue({
      projects: [
        {
          id: "1",
          name: "my-repo",
          status: "ready",
          languages: [],
          created_at: "",
          updated_at: "",
        },
      ],
    });
    render(<ProjectList />, { wrapper: Wrapper });
    await screen.findByText("my-repo");
  });
});
