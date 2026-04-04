// ─────────────────────────────────────────────────────────────────────────────
// SFOACC React Query hooks
//
// Requirements: @tanstack/react-query v5
//   npm install @tanstack/react-query
//
// Setup in your app root:
//   import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
//   const queryClient = new QueryClient();
//   <QueryClientProvider client={queryClient}>...</QueryClientProvider>
//
// Usage example:
//   const { data: parish } = useParish(client);
//   const { data: parishioners } = useParishioners(client, { limit: 20 });
// ─────────────────────────────────────────────────────────────────────────────

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { SFOACCClient, type APIError } from "./client";
import type {
  ParishDetail,
  ChurchUnit,
  ChurchUnitCreate,
  ChurchUnitUpdate,
  OutstationDetail,
  MassSchedule,
  MassScheduleCreate,
  MassScheduleUpdate,
  LeadershipCreate,
  LeadershipUpdate,
  LeadershipRead,
  ChurchEventCreate,
  ChurchEventUpdate,
  ChurchEventRead,
  Society,
  SocietyCreate,
  SocietyUpdate,
  ChurchCommunity,
  ChurchCommunityCreate,
  ChurchCommunityUpdate,
  Parishioner,
  ParishionerCreate,
  ParishionerUpdate,
  ParishionerDetailed,
  ParishionerFilters,
  User,
  UserCreate,
  UserUpdate,
  RoleRead,
  RoleCreate,
  RoleUpdate,
  RolePermissionsUpdate,
  PermissionRead,
  SettingRead,
  SettingsBulkUpdate,
  AppConfigUpdate,
  AuthConfigUpdate,
  ScheduledMessageRead,
  PaginationParams,
  PagedData,
} from "./types";

// ── Query key factory ─────────────────────────────────────────────────────────

export const queryKeys = {
  groups: () => ["groups"] as const,
  churchUnitsPublic: () => ["church-units-public"] as const,
  parish: () => ["parish"] as const,
  outstations: (params?: PaginationParams) =>
    ["outstations", params] as const,
  outstation: (id: number) => ["outstation", id] as const,
  parishSchedules: () => ["parish", "schedules"] as const,
  outstationSchedules: (id: number) =>
    ["outstation", id, "schedules"] as const,
  churchUnits: (params?: PaginationParams) =>
    ["church-units", params] as const,
  churchUnit: (id: number) => ["church-unit", id] as const,
  parishLeadership: (currentOnly?: boolean) =>
    ["parish", "leadership", currentOnly] as const,
  unitLeadership: (unitId: number, currentOnly?: boolean) =>
    ["church-unit", unitId, "leadership", currentOnly] as const,
  parishEvents: (params?: object) => ["parish", "events", params] as const,
  unitEvents: (unitId: number, params?: object) =>
    ["church-unit", unitId, "events", params] as const,
  societies: (
    params?: PaginationParams & { search?: string; church_unit_id?: number }
  ) => ["societies", params] as const,
  society: (id: number) => ["society", id] as const,
  societyMembers: (id: number) => ["society", id, "members"] as const,
  communities: (params?: PaginationParams & { search?: string }) =>
    ["communities", params] as const,
  community: (id: number) => ["community", id] as const,
  parishioners: (filters?: ParishionerFilters) =>
    ["parishioners", filters] as const,
  parishioner: (id: string) => ["parishioner", id] as const,
  users: (params?: PaginationParams) => ["users", params] as const,
  user: (id: string) => ["user", id] as const,
};

// ── Public reference data (no token needed) ───────────────────────────────────

/** Fetch app branding/contact config. Public, no token. Cached indefinitely (staleTime: Infinity). */
export function useAppConfig(client: SFOACCClient) {
  return useQuery({
    queryKey: ["app-config"] as const,
    queryFn: () => client.getAppConfig(),
    staleTime: Infinity,
  });
}

/**
 * Fetch everything the login page needs in one call:
 *   data.login_methods  — { password, otp_email, otp_sms }
 *   data.groups         — [{ name, label, description }]
 *   data.church_units   — [{ id, name, type }]
 *
 * Cached indefinitely (staleTime: Infinity). Call before login.
 */
export function useLoginConfig(client: SFOACCClient) {
  return useQuery({
    queryKey: ["login-config"] as const,
    queryFn: () => client.getLoginConfig(),
    staleTime: Infinity,
  });
}

/** Fetch all available groups. Safe to call before login. Cached indefinitely (staleTime: Infinity). */
export function useGroups(client: SFOACCClient) {
  return useQuery({
    queryKey: queryKeys.groups(),
    queryFn: () => client.listGroups(),
    staleTime: Infinity,
  });
}

/** Fetch all active church units. Safe to call before login. Cached indefinitely (staleTime: Infinity). */
export function useChurchUnitsPublic(client: SFOACCClient) {
  return useQuery({
    queryKey: queryKeys.churchUnitsPublic(),
    queryFn: () => client.listChurchUnitsPublic(),
    staleTime: Infinity,
  });
}

// ── Parish ────────────────────────────────────────────────────────────────────

export function useParish(
  client: SFOACCClient,
  options?: Omit<UseQueryOptions<ParishDetail | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.parish(),
    queryFn: async () => {
      const res = await client.getParish();
      return res.data;
    },
    ...options,
  });
}

export function useUpdateParish(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ChurchUnitUpdate) => client.updateParish(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.parish() }),
  });
}

// ── Outstations ───────────────────────────────────────────────────────────────

export function useOutstations(
  client: SFOACCClient,
  params: PaginationParams = {},
  options?: Omit<UseQueryOptions<PagedData<ChurchUnit> | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.outstations(params),
    queryFn: async () => {
      const res = await client.listOutstations(params);
      return res.data;
    },
    ...options,
  });
}

export function useOutstation(
  client: SFOACCClient,
  id: number,
  options?: Omit<UseQueryOptions<OutstationDetail | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.outstation(id),
    queryFn: async () => {
      const res = await client.getOutstation(id);
      return res.data;
    },
    ...options,
  });
}

export function useCreateOutstation(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Omit<ChurchUnitCreate, "type">) =>
      client.createOutstation(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["outstations"] });
      qc.invalidateQueries({ queryKey: queryKeys.parish() });
    },
  });
}

export function useUpdateOutstation(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ChurchUnitUpdate }) =>
      client.updateOutstation(id, data),
    onSuccess: (_: unknown, vars: { id: number; data: ChurchUnitUpdate }) => {
      qc.invalidateQueries({ queryKey: queryKeys.outstation(vars.id) });
      qc.invalidateQueries({ queryKey: ["outstations"] });
      qc.invalidateQueries({ queryKey: queryKeys.parish() });
    },
  });
}

export function useDeleteOutstation(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.deleteOutstation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["outstations"] });
      qc.invalidateQueries({ queryKey: queryKeys.parish() });
    },
  });
}

// ── Mass Schedules ────────────────────────────────────────────────────────────

export function useParishSchedules(
  client: SFOACCClient,
  options?: Omit<UseQueryOptions<MassSchedule[] | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.parishSchedules(),
    queryFn: async () => {
      const res = await client.listParishSchedules();
      return res.data;
    },
    ...options,
  });
}

export function useCreateParishSchedule(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MassScheduleCreate) =>
      client.createParishSchedule(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.parishSchedules() }),
  });
}

export function useUpdateParishSchedule(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: MassScheduleUpdate }) =>
      client.updateParishSchedule(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.parishSchedules() }),
  });
}

export function useDeleteParishSchedule(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.deleteParishSchedule(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.parishSchedules() }),
  });
}

export function useOutstationSchedules(
  client: SFOACCClient,
  outstationId: number,
  options?: Omit<UseQueryOptions<MassSchedule[] | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.outstationSchedules(outstationId),
    queryFn: async () => {
      const res = await client.listOutstationSchedules(outstationId);
      return res.data;
    },
    ...options,
  });
}

export function useCreateOutstationSchedule(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      outstationId,
      data,
    }: {
      outstationId: number;
      data: MassScheduleCreate;
    }) => client.createOutstationSchedule(outstationId, data),
    onSuccess: (_: unknown, vars: { outstationId: number; data: MassScheduleCreate }) =>
      qc.invalidateQueries({
        queryKey: queryKeys.outstationSchedules(vars.outstationId),
      }),
  });
}

// ── Societies ─────────────────────────────────────────────────────────────────

export function useSocieties(
  client: SFOACCClient,
  params: PaginationParams & { search?: string; church_unit_id?: number } = {},
  options?: Omit<UseQueryOptions<PagedData<Society> | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.societies(params),
    queryFn: async () => {
      const res = await client.listSocieties(params);
      return res.data;
    },
    ...options,
  });
}

export function useSociety(
  client: SFOACCClient,
  id: number,
  options?: Omit<UseQueryOptions<Society | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.society(id),
    queryFn: async () => {
      const res = await client.getSociety(id);
      return res.data;
    },
    ...options,
  });
}

export function useCreateSociety(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SocietyCreate) => client.createSociety(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["societies"] }),
  });
}

export function useUpdateSociety(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: SocietyUpdate }) =>
      client.updateSociety(id, data),
    onSuccess: (_: unknown, vars: { id: number; data: SocietyUpdate }) => {
      qc.invalidateQueries({ queryKey: queryKeys.society(vars.id) });
      qc.invalidateQueries({ queryKey: ["societies"] });
    },
  });
}

export function useDeleteSociety(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.deleteSociety(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["societies"] }),
  });
}

// ── Church Communities ────────────────────────────────────────────────────────

export function useCommunities(
  client: SFOACCClient,
  params: PaginationParams & { search?: string } = {},
  options?: Omit<UseQueryOptions<PagedData<ChurchCommunity> | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.communities(params),
    queryFn: async () => {
      const res = await client.listCommunities(params);
      return res.data;
    },
    ...options,
  });
}

export function useCommunity(
  client: SFOACCClient,
  id: number,
  options?: Omit<UseQueryOptions<ChurchCommunity | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.community(id),
    queryFn: async () => {
      const res = await client.getCommunity(id);
      return res.data;
    },
    ...options,
  });
}

export function useCreateCommunity(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ChurchCommunityCreate) =>
      client.createCommunity(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["communities"] }),
  });
}

export function useUpdateCommunity(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ChurchCommunityUpdate }) =>
      client.updateCommunity(id, data),
    onSuccess: (_: unknown, vars: { id: number; data: ChurchCommunityUpdate }) => {
      qc.invalidateQueries({ queryKey: queryKeys.community(vars.id) });
      qc.invalidateQueries({ queryKey: ["communities"] });
    },
  });
}

export function useDeleteCommunity(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.deleteCommunity(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["communities"] }),
  });
}

// ── Parishioners ──────────────────────────────────────────────────────────────

export function useParishioners(
  client: SFOACCClient,
  filters: ParishionerFilters = {},
  options?: Omit<UseQueryOptions<PagedData<Parishioner> | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.parishioners(filters),
    queryFn: async () => {
      const res = await client.listParishioners(filters);
      return res.data;
    },
    ...options,
  });
}

export function useParishioner(
  client: SFOACCClient,
  id: string,
  options?: Omit<UseQueryOptions<ParishionerDetailed | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.parishioner(id),
    queryFn: async () => {
      const res = await client.getParishioner(id);
      return res.data;
    },
    ...options,
  });
}

export function useCreateParishioner(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ParishionerCreate) =>
      client.createParishioner(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parishioners"] }),
  });
}

export function useUpdateParishioner(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ParishionerUpdate }) =>
      client.updateParishioner(id, data),
    onSuccess: (_: unknown, vars: { id: string; data: ParishionerUpdate }) => {
      qc.invalidateQueries({ queryKey: queryKeys.parishioner(vars.id) });
      qc.invalidateQueries({ queryKey: ["parishioners"] });
    },
  });
}

// ── Users ──────────────────────────────────────────────────────────────────────

export function useUsers(
  client: SFOACCClient,
  params: PaginationParams = {},
  options?: Omit<UseQueryOptions<PagedData<User> | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.users(params),
    queryFn: async () => {
      const res = await client.listUsers(params);
      return res.data as PagedData<User> | null;
    },
    ...options,
  });
}

export function useUser(
  client: SFOACCClient,
  id: string,
  options?: Omit<UseQueryOptions<User | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.user(id),
    queryFn: async () => {
      const res = await client.getUser(id);
      return res.data;
    },
    ...options,
  });
}

export function useCreateUser(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: UserCreate) => client.createUser(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useUpdateUser(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UserUpdate }) =>
      client.updateUser(id, data),
    onSuccess: (_: unknown, vars: { id: string; data: UserUpdate }) => {
      qc.invalidateQueries({ queryKey: queryKeys.user(vars.id) });
      qc.invalidateQueries({ queryKey: ["users"] });
    },
  });
}

export function useDeleteUser(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => client.deleteUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}

// ── Leadership ────────────────────────────────────────────────────────────────

export function useParishLeadership(
  client: SFOACCClient,
  currentOnly = true,
  options?: Omit<UseQueryOptions<LeadershipRead[] | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.parishLeadership(currentOnly),
    queryFn: async () => {
      const res = await client.listParishLeadership(currentOnly);
      return res.data;
    },
    ...options,
  });
}

export function useCreateParishLeadership(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LeadershipCreate) => client.createParishLeadership(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parish", "leadership"] }),
  });
}

export function useUpdateParishLeadership(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: LeadershipUpdate }) =>
      client.updateParishLeadership(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parish", "leadership"] }),
  });
}

export function useDeleteParishLeadership(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.deleteParishLeadership(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parish", "leadership"] }),
  });
}

export function useUnitLeadership(
  client: SFOACCClient,
  unitId: number,
  currentOnly = true,
  options?: Omit<UseQueryOptions<LeadershipRead[] | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.unitLeadership(unitId, currentOnly),
    queryFn: async () => {
      const res = await client.listUnitLeadership(unitId, currentOnly);
      return res.data;
    },
    ...options,
  });
}

export function useCreateUnitLeadership(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ unitId, data }: { unitId: number; data: LeadershipCreate }) =>
      client.createUnitLeadership(unitId, data),
    onSuccess: (_: unknown, vars: { unitId: number; data: LeadershipCreate }) =>
      qc.invalidateQueries({ queryKey: ["church-unit", vars.unitId, "leadership"] }),
  });
}

export function useUpdateUnitLeadership(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ unitId, id, data }: { unitId: number; id: number; data: LeadershipUpdate }) =>
      client.updateUnitLeadership(unitId, id, data),
    onSuccess: (_: unknown, vars: { unitId: number; id: number; data: LeadershipUpdate }) =>
      qc.invalidateQueries({ queryKey: ["church-unit", vars.unitId, "leadership"] }),
  });
}

export function useDeleteUnitLeadership(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ unitId, id }: { unitId: number; id: number }) =>
      client.deleteUnitLeadership(unitId, id),
    onSuccess: (_: unknown, vars: { unitId: number; id: number }) =>
      qc.invalidateQueries({ queryKey: ["church-unit", vars.unitId, "leadership"] }),
  });
}

// ── Church Events ─────────────────────────────────────────────────────────────

type EventParams = { upcoming_only?: boolean; from_date?: string; to_date?: string };

export function useParishEvents(
  client: SFOACCClient,
  params: EventParams = {},
  options?: Omit<UseQueryOptions<ChurchEventRead[] | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.parishEvents(params),
    queryFn: async () => {
      const res = await client.listParishEvents(params);
      return res.data;
    },
    ...options,
  });
}

export function useCreateParishEvent(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ChurchEventCreate) => client.createParishEvent(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parish", "events"] }),
  });
}

export function useUpdateParishEvent(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ChurchEventUpdate }) =>
      client.updateParishEvent(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parish", "events"] }),
  });
}

export function useDeleteParishEvent(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.deleteParishEvent(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["parish", "events"] }),
  });
}

export function useUnitEvents(
  client: SFOACCClient,
  unitId: number,
  params: EventParams = {},
  options?: Omit<UseQueryOptions<ChurchEventRead[] | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: queryKeys.unitEvents(unitId, params),
    queryFn: async () => {
      const res = await client.listUnitEvents(unitId, params);
      return res.data;
    },
    ...options,
  });
}

export function useCreateUnitEvent(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ unitId, data }: { unitId: number; data: ChurchEventCreate }) =>
      client.createUnitEvent(unitId, data),
    onSuccess: (_: unknown, vars: { unitId: number; data: ChurchEventCreate }) =>
      qc.invalidateQueries({ queryKey: ["church-unit", vars.unitId, "events"] }),
  });
}

export function useUpdateUnitEvent(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ unitId, id, data }: { unitId: number; id: number; data: ChurchEventUpdate }) =>
      client.updateUnitEvent(unitId, id, data),
    onSuccess: (_: unknown, vars: { unitId: number; id: number; data: ChurchEventUpdate }) =>
      qc.invalidateQueries({ queryKey: ["church-unit", vars.unitId, "events"] }),
  });
}

export function useDeleteUnitEvent(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ unitId, id }: { unitId: number; id: number }) =>
      client.deleteUnitEvent(unitId, id),
    onSuccess: (_: unknown, vars: { unitId: number; id: number }) =>
      qc.invalidateQueries({ queryKey: ["church-unit", vars.unitId, "events"] }),
  });
}

// ── Admin Settings ────────────────────────────────────────────────────────────

export function useSettings(
  client: SFOACCClient,
  options?: Omit<UseQueryOptions<SettingRead[] | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: ["admin", "settings"] as const,
    queryFn: async () => {
      const res = await client.getSettings();
      return res.data;
    },
    ...options,
  });
}

export function useUpdateSettings(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SettingsBulkUpdate) => client.updateSettings(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "settings"] }),
  });
}

export function useAppSettings(
  client: SFOACCClient,
  options?: Omit<UseQueryOptions<Record<string, string | null> | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: ["admin", "settings", "app"] as const,
    queryFn: async () => {
      const res = await client.getAppSettings();
      return res.data;
    },
    ...options,
  });
}

export function useUpdateAppSettings(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AppConfigUpdate) => client.updateAppSettings(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "settings", "app"] });
      qc.invalidateQueries({ queryKey: ["app-config"] });
    },
  });
}

export function useAuthSettings(
  client: SFOACCClient,
  options?: Omit<UseQueryOptions<Record<string, string | null> | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: ["admin", "settings", "auth"] as const,
    queryFn: async () => {
      const res = await client.getAuthSettings();
      return res.data;
    },
    ...options,
  });
}

export function useUpdateAuthSettings(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AuthConfigUpdate) => client.updateAuthSettings(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "settings", "auth"] });
      qc.invalidateQueries({ queryKey: ["login-config"] });
    },
  });
}

// ── Roles & Permissions ───────────────────────────────────────────────────────

export function usePermissions(
  client: SFOACCClient,
  options?: Omit<UseQueryOptions<PermissionRead[] | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: ["admin", "permissions"] as const,
    queryFn: async () => {
      const res = await client.listPermissions();
      return res.data;
    },
    staleTime: 5 * 60 * 1000, // permissions rarely change
    ...options,
  });
}

export function useRoles(
  client: SFOACCClient,
  options?: Omit<UseQueryOptions<RoleRead[] | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: ["admin", "roles"] as const,
    queryFn: async () => {
      const res = await client.listRoles();
      return res.data;
    },
    ...options,
  });
}

export function useRole(
  client: SFOACCClient,
  id: number,
  options?: Omit<UseQueryOptions<RoleRead | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: ["admin", "role", id] as const,
    queryFn: async () => {
      const res = await client.getRole(id);
      return res.data;
    },
    ...options,
  });
}

export function useCreateRole(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: RoleCreate) => client.createRole(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "roles"] }),
  });
}

export function useUpdateRole(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: RoleUpdate }) =>
      client.updateRole(id, data),
    onSuccess: (_: unknown, vars: { id: number; data: RoleUpdate }) => {
      qc.invalidateQueries({ queryKey: ["admin", "role", vars.id] });
      qc.invalidateQueries({ queryKey: ["admin", "roles"] });
    },
  });
}

export function useDeleteRole(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.deleteRole(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "roles"] }),
  });
}

export function useSetRolePermissions(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: RolePermissionsUpdate }) =>
      client.setRolePermissions(id, data),
    onSuccess: (_: unknown, vars: { id: number; data: RolePermissionsUpdate }) => {
      qc.invalidateQueries({ queryKey: ["admin", "role", vars.id] });
      qc.invalidateQueries({ queryKey: ["admin", "roles"] });
    },
  });
}

// ── Messaging ─────────────────────────────────────────────────────────────────

export function useMessageTemplates(client: SFOACCClient) {
  return useQuery({
    queryKey: ["messaging", "templates"] as const,
    queryFn: async () => {
      const res = await client.getMessageTemplates();
      return res.data;
    },
    staleTime: 10 * 60 * 1000,
  });
}

export function useSendBulkMessage(client: SFOACCClient) {
  return useMutation({
    mutationFn: (data: Parameters<typeof client.sendBulkMessage>[0]) =>
      client.sendBulkMessage(data),
  });
}

export function useScheduleMessage(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof client.scheduleMessage>[0]) =>
      client.scheduleMessage(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["messaging", "scheduled"] }),
  });
}

export function useScheduledMessages(
  client: SFOACCClient,
  params: { status_filter?: string; skip?: number; limit?: number } = {},
  options?: Omit<UseQueryOptions<PagedData<ScheduledMessageRead> | null, APIError>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: ["messaging", "scheduled", params] as const,
    queryFn: async () => {
      const res = await client.listScheduledMessages(params);
      return res.data;
    },
    ...options,
  });
}

export function useCancelScheduledMessage(client: SFOACCClient) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.cancelScheduledMessage(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["messaging", "scheduled"] }),
  });
}
