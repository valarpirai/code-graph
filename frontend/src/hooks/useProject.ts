import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listProjects,
  getProject,
  deleteProject,
  reindexProject,
  pullProject,
  switchBranch,
  listBranches,
} from "../api/client";

export const projectKeys = {
  all: ["projects"] as const,
  detail: (id: string) => ["projects", id] as const,
};

export function useProjects() {
  return useQuery({
    queryKey: projectKeys.all,
    queryFn: listProjects,
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => getProject(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "indexing" || status === "cloning" ? 3000 : false;
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteProject,
    onSuccess: () => qc.invalidateQueries({ queryKey: projectKeys.all }),
  });
}

export function useReindexProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: reindexProject,
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: projectKeys.detail(id) });
    },
  });
}

export function usePullProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: pullProject,
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: projectKeys.detail(id) });
    },
  });
}

export function useSwitchBranch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, branch }: { id: string; branch: string }) =>
      switchBranch(id, branch),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: projectKeys.detail(id) });
    },
  });
}

export function useBranches(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["projects", id, "branches"] as const,
    queryFn: () => listBranches(id),
    enabled,
    staleTime: 60_000,
  });
}
