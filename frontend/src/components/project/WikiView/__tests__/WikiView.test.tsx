import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import WikiView from "../index";
import * as client from "../../../../api/client";

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
);

describe("WikiView", () => {
  it("shows 'no wiki pages' when list is empty", async () => {
    vi.spyOn(client, "listWikiFiles").mockResolvedValue({ files: [] });
    render(<WikiView projectId="p1" />, { wrapper: Wrapper });
    await screen.findByText(/No wiki pages yet/i);
  });

  it("renders file list and content on selection", async () => {
    vi.spyOn(client, "listWikiFiles").mockResolvedValue({
      files: [{ name: "overview.md", path: "wiki/overview.md" }],
    });
    vi.spyOn(client, "getWikiContent").mockResolvedValue({
      name: "overview.md",
      content: "# Overview\nHello world",
    });
    render(<WikiView projectId="p1" />, { wrapper: Wrapper });
    const btn = await screen.findByText("overview");
    fireEvent.click(btn);
    await waitFor(() => screen.getByText(/Hello world/i));
  });
});
