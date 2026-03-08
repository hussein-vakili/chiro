import { DependencyList } from "react";
import { useMutation, UseMutationOptions, useQuery } from "@tanstack/react-query";

export interface ApiResourceState<T> {
  loading: boolean;
  data: T | null;
  error: string;
  errorPayload: unknown;
  queryKey: readonly unknown[];
  reload: () => Promise<void>;
}

interface ApiResponseShape {
  ok?: boolean;
  error?: string;
  errors?: string[];
}

interface ApiMutationResult<TData> {
  response: Response;
  data: TData & ApiResponseShape;
}

interface ApiMutationContext<TData, TVariables> extends Omit<UseMutationOptions<TData, ApiResourceError, TVariables>, "mutationFn"> {}

interface ApiResourceOptions {
  queryKey?: readonly unknown[];
  enabled?: boolean;
  staleTime?: number;
  retry?: number | boolean;
}

class ApiResourceError extends Error {
  errorPayload: unknown;

  constructor(message: string, errorPayload: unknown) {
    super(message);
    this.name = "ApiResourceError";
    this.errorPayload = errorPayload;
  }
}

async function resolveApiResource<T>(
  loadFn: () => Promise<{ response: Response; data: T & ApiResponseShape }>
): Promise<T> {
  const { response, data } = await loadFn();
  if (!response.ok || data.ok === false) {
    const message = data.error || (data.errors ? data.errors.join(" ") : `Request failed (${response.status})`);
    throw new ApiResourceError(message, data || null);
  }
  return data;
}

export function useApiResource<T>(
  loadFn: () => Promise<{ response: Response; data: T & { ok?: boolean; error?: string; errors?: string[] } }>,
  deps: DependencyList,
  options: ApiResourceOptions = {}
): ApiResourceState<T> {
  const queryKey = options.queryKey || ["api-resource", ...deps];
  const query = useQuery<T, ApiResourceError>({
    queryKey,
    queryFn: () => resolveApiResource(loadFn),
    staleTime: options.staleTime ?? 30_000,
    retry: options.retry ?? 1,
    enabled: options.enabled ?? true,
  });

  return {
    loading: query.isLoading && !query.data,
    data: query.data ?? null,
    error: query.error?.message || "",
    errorPayload: query.error?.errorPayload ?? null,
    queryKey,
    reload: async () => {
      await query.refetch();
    },
  };
}

export function useApiMutation<TData, TVariables>(
  mutateFn: (variables: TVariables) => Promise<ApiMutationResult<TData>>,
  options: ApiMutationContext<TData, TVariables> = {}
) {
  return useMutation<TData, ApiResourceError, TVariables>({
    ...options,
    mutationFn: async (variables) => resolveApiResource(() => mutateFn(variables)),
  });
}
