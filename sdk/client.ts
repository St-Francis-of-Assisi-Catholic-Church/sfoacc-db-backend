// ─────────────────────────────────────────────────────────────────────────────
// SFOACC API Client
// Usage:
//   const client = new SFOACCClient({ baseUrl: "https://yourapi.com" });
//   // after login, set the token:
//   client.setToken(loginResponse.access_token);
// ─────────────────────────────────────────────────────────────────────────────

import type {
  APIResponse,
  PagedData,
  PagedResponse,
  LoginResponse,
  OTPRequestBody,  // eslint-disable-line @typescript-eslint/no-unused-vars
  OTPVerifyBody,   // eslint-disable-line @typescript-eslint/no-unused-vars
  PasswordResetRequest,
  PasswordResetResponse,
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
  SocietyMember,
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
} from "./types";

export class APIError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "APIError";
  }
}

export interface SFOACCClientConfig {
  /** Base URL of the API, e.g. "https://api.yourdomain.com" */
  baseUrl: string;
  /** Optional initial token */
  token?: string;
}

export class SFOACCClient {
  private baseUrl: string;
  private token: string | null;

  constructor(config: SFOACCClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, "");
    this.token = config.token ?? null;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  private get headers(): HeadersInit {
    return {
      "Content-Type": "application/json",
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
    };
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: { ...this.headers, ...(options.headers ?? {}) },
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      const detail = body?.detail ?? res.statusText;
      throw new APIError(res.status, detail);
    }
    return res.json() as Promise<T>;
  }

  private buildQuery(params: object): string {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params as Record<string, unknown>)) {
      if (v !== undefined && v !== null) q.set(k, String(v));
    }
    const s = q.toString();
    return s ? `?${s}` : "";
  }

  // ── Auth ──────────────────────────────────────────────────────────────────

  // ── App info (public, no token) ────────────────────────────────────────────

  /** Public — app branding and contact config (name, description, contact_email, etc.). */
  getAppConfig(): Promise<{
    data: {
      name: string;
      description: string;
      version: string;
      church_code: string;
      currency_symbol: string;
      currency_code: string;
      contact_email: string;
      contact_phone: string;
      website: string;
      address: string;
      logo_url: string;
      support_email: string;
    };
  }> {
    return this.request("/api/v1/app/config");
  }

  /**
   * Public — everything the login page needs: enabled login methods, groups, church units.
   * Call this once on app load (before login) to drive login form rendering.
   */
  getLoginConfig(): Promise<{
    data: {
      login_methods: { password: boolean; otp_email: boolean; otp_sms: boolean };
      groups: Array<{ name: string; label: string; description: string }>;
      church_units: Array<{ id: number; name: string; type: string }>;
    };
  }> {
    return this.request("/api/v1/app/login-config");
  }

  /** Public — list available groups for dropdown population. No token required. */
  listGroups(): Promise<{ data: Array<{ name: string; label: string; description: string }> }> {
    return this.request("/api/v1/app/groups");
  }

  /** Public — list all active church units for login/user-creation dropdowns. No token required. */
  listChurchUnitsPublic(): Promise<{ data: Array<{ id: number; name: string; type: "parish" | "outstation" }> }> {
    return this.request("/api/v1/app/church-units");
  }

  /** Login and automatically store the returned token. */
  async login(email: string, password: string): Promise<LoginResponse> {
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: "POST",
      body,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new APIError(res.status, err?.detail ?? res.statusText);
    }
    const data: LoginResponse = await res.json();
    this.token = data.access_token;
    return data;
  }

  async resetPassword(
    payload: PasswordResetRequest
  ): Promise<APIResponse<PasswordResetResponse>> {
    return this.request("/api/v1/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  /**
   * Request an OTP code. Always resolves (202) regardless of whether the email
   * exists — do not treat a successful response as proof the user exists.
   */
  /**
   * Request a one-time login code.
   * The code is sent to ALL available channels (email + SMS) simultaneously.
   * @param identifier  Email address OR phone number with country code (e.g. 233543460633)
   */
  async requestOtp(identifier: string): Promise<APIResponse<null>> {
    const body: OTPRequestBody = { identifier };
    return this.request("/api/v1/auth/otp/request", {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  /**
   * Verify an OTP code and receive a JWT token.
   * @param identifier  Email address OR phone number with country code
   */
  async verifyOtp(identifier: string, code: string): Promise<LoginResponse> {
    const body: OTPVerifyBody = { identifier, code };
    const res = await this.request<LoginResponse>("/api/v1/auth/otp/verify", {
      method: "POST",
      body: JSON.stringify(body),
    });
    this.token = res.access_token;
    return res;
  }

  // ── Parish ────────────────────────────────────────────────────────────────

  /** Full parish detail including outstations, schedules, societies, communities. */
  getParish(): Promise<APIResponse<ParishDetail>> {
    return this.request("/api/v1/parish");
  }

  updateParish(data: ChurchUnitUpdate): Promise<APIResponse<ChurchUnit>> {
    return this.request("/api/v1/parish", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  // ── Outstations ──────────────────────────────────────────────────────────

  listOutstations(
    params: PaginationParams = {}
  ): Promise<PagedResponse<ChurchUnit>> {
    return this.request(`/api/v1/parish/outstations${this.buildQuery(params)}`);
  }

  getOutstation(id: number): Promise<APIResponse<OutstationDetail>> {
    return this.request(`/api/v1/parish/outstations/${id}`);
  }

  createOutstation(
    data: Omit<ChurchUnitCreate, "type">
  ): Promise<APIResponse<ChurchUnit>> {
    return this.request("/api/v1/parish/outstations", {
      method: "POST",
      body: JSON.stringify({ ...data, type: "OUTSTATION" }),
    });
  }

  updateOutstation(
    id: number,
    data: ChurchUnitUpdate
  ): Promise<APIResponse<ChurchUnit>> {
    return this.request(`/api/v1/parish/outstations/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  deleteOutstation(id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/parish/outstations/${id}`, {
      method: "DELETE",
    });
  }

  // ── Mass Schedules ────────────────────────────────────────────────────────

  listParishSchedules(): Promise<APIResponse<MassSchedule[]>> {
    return this.request("/api/v1/parish/mass-schedules");
  }

  createParishSchedule(
    data: MassScheduleCreate
  ): Promise<APIResponse<MassSchedule>> {
    return this.request("/api/v1/parish/mass-schedules", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  updateParishSchedule(
    id: number,
    data: MassScheduleUpdate
  ): Promise<APIResponse<MassSchedule>> {
    return this.request(`/api/v1/parish/mass-schedules/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  deleteParishSchedule(id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/parish/mass-schedules/${id}`, {
      method: "DELETE",
    });
  }

  listOutstationSchedules(
    outstationId: number
  ): Promise<APIResponse<MassSchedule[]>> {
    return this.request(
      `/api/v1/parish/outstations/${outstationId}/mass-schedules`
    );
  }

  createOutstationSchedule(
    outstationId: number,
    data: MassScheduleCreate
  ): Promise<APIResponse<MassSchedule>> {
    return this.request(
      `/api/v1/parish/outstations/${outstationId}/mass-schedules`,
      { method: "POST", body: JSON.stringify(data) }
    );
  }

  updateOutstationSchedule(
    outstationId: number,
    scheduleId: number,
    data: MassScheduleUpdate
  ): Promise<APIResponse<MassSchedule>> {
    return this.request(
      `/api/v1/parish/outstations/${outstationId}/mass-schedules/${scheduleId}`,
      { method: "PUT", body: JSON.stringify(data) }
    );
  }

  deleteOutstationSchedule(
    outstationId: number,
    scheduleId: number
  ): Promise<APIResponse<null>> {
    return this.request(
      `/api/v1/parish/outstations/${outstationId}/mass-schedules/${scheduleId}`,
      { method: "DELETE" }
    );
  }

  // ── Church Units (generic) ────────────────────────────────────────────────

  listChurchUnits(
    params: PaginationParams = {}
  ): Promise<PagedResponse<ChurchUnit>> {
    return this.request(`/api/v1/parish/units${this.buildQuery(params)}`);
  }

  getChurchUnit(id: number): Promise<APIResponse<OutstationDetail>> {
    return this.request(`/api/v1/parish/units/${id}`);
  }

  createChurchUnit(data: ChurchUnitCreate): Promise<APIResponse<ChurchUnit>> {
    return this.request("/api/v1/parish/units", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  updateChurchUnit(
    id: number,
    data: ChurchUnitUpdate
  ): Promise<APIResponse<ChurchUnit>> {
    return this.request(`/api/v1/parish/units/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  deleteChurchUnit(id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/parish/units/${id}`, { method: "DELETE" });
  }

  // ── Societies ─────────────────────────────────────────────────────────────

  listSocieties(
    params: PaginationParams & {
      search?: string;
      church_unit_id?: number;
    } = {}
  ): Promise<PagedResponse<Society>> {
    return this.request(`/api/v1/societies/all${this.buildQuery(params)}`);
  }

  getSociety(id: number): Promise<APIResponse<Society>> {
    return this.request(`/api/v1/societies/${id}`);
  }

  createSociety(data: SocietyCreate): Promise<APIResponse<Society>> {
    return this.request("/api/v1/societies", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  updateSociety(id: number, data: SocietyUpdate): Promise<APIResponse<Society>> {
    return this.request(`/api/v1/societies/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  deleteSociety(id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/societies/${id}`, { method: "DELETE" });
  }

  getSocietyMembers(id: number): Promise<APIResponse<SocietyMember[]>> {
    return this.request(`/api/v1/societies/${id}/members`);
  }

  addSocietyMembers(
    id: number,
    members: Array<{ parishioner_id: string; date_joined?: string }>
  ): Promise<APIResponse<null>> {
    return this.request(`/api/v1/societies/${id}/members`, {
      method: "POST",
      body: JSON.stringify({ members }),
    });
  }

  removeSocietyMembers(
    id: number,
    parishioner_ids: string[]
  ): Promise<APIResponse<null>> {
    return this.request(`/api/v1/societies/${id}/members`, {
      method: "DELETE",
      body: JSON.stringify({ parishioner_ids }),
    });
  }

  // ── Church Communities ────────────────────────────────────────────────────

  listCommunities(
    params: PaginationParams & { search?: string } = {}
  ): Promise<PagedResponse<ChurchCommunity>> {
    return this.request(
      `/api/v1/church-community/all${this.buildQuery(params)}`
    );
  }

  getCommunity(id: number): Promise<APIResponse<ChurchCommunity>> {
    return this.request(`/api/v1/church-community/${id}`);
  }

  createCommunity(
    data: ChurchCommunityCreate
  ): Promise<APIResponse<ChurchCommunity>> {
    return this.request("/api/v1/church-community", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  updateCommunity(
    id: number,
    data: ChurchCommunityUpdate
  ): Promise<APIResponse<ChurchCommunity>> {
    return this.request(`/api/v1/church-community/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  deleteCommunity(id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/church-community/${id}`, {
      method: "DELETE",
    });
  }

  // ── Parishioners ──────────────────────────────────────────────────────────

  listParishioners(
    filters: ParishionerFilters = {}
  ): Promise<PagedResponse<Parishioner>> {
    return this.request(`/api/v1/parishioners/all${this.buildQuery(filters)}`);
  }

  getParishioner(id: string): Promise<APIResponse<ParishionerDetailed>> {
    return this.request(`/api/v1/parishioners/${id}`);
  }

  createParishioner(
    data: ParishionerCreate
  ): Promise<APIResponse<Parishioner>> {
    return this.request("/api/v1/parishioners", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  updateParishioner(
    id: string,
    data: ParishionerUpdate
  ): Promise<APIResponse<Parishioner>> {
    return this.request(`/api/v1/parishioners/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  generateChurchId(
    id: string,
    oldChurchId: string,
    opts: { send_email?: boolean; send_sms?: boolean } = {}
  ): Promise<APIResponse<{ old_church_id: string; new_church_id: string }>> {
    return this.request(
      `/api/v1/parishioners/${id}/generate-church-id${this.buildQuery({ old_church_id: oldChurchId, ...opts })}`
    );
  }

  // ── Sacraments ────────────────────────────────────────────────────────────

  listSacraments(): Promise<APIResponse<unknown[]>> {
    return this.request("/api/v1/sacraments/all");
  }

  getSacrament(id: number): Promise<APIResponse<unknown>> {
    return this.request(`/api/v1/sacraments/${id}`);
  }

  getSacramentRecipients(id: number | string): Promise<APIResponse<unknown[]>> {
    return this.request(`/api/v1/sacraments/${id}/recipients`);
  }

  // ── Admin Settings ─────────────────────────────────────────────────────────

  /** Get all raw settings as a list of SettingRead. */
  getSettings(): Promise<APIResponse<SettingRead[]>> {
    return this.request("/api/v1/admin/settings");
  }

  /** Bulk-update settings by key→value map. */
  updateSettings(data: SettingsBulkUpdate): Promise<APIResponse<SettingRead[]>> {
    return this.request("/api/v1/admin/settings", { method: "PUT", body: JSON.stringify(data) });
  }

  /** Get app branding/contact config (name, description, contact_email, etc.). */
  getAppSettings(): Promise<APIResponse<Record<string, string | null>>> {
    return this.request("/api/v1/admin/settings/app");
  }

  /** Update app branding/contact config. */
  updateAppSettings(data: AppConfigUpdate): Promise<APIResponse<Record<string, string | null>>> {
    return this.request("/api/v1/admin/settings/app", { method: "PUT", body: JSON.stringify(data) });
  }

  /** Get auth method config (login methods, OTP). */
  getAuthSettings(): Promise<APIResponse<Record<string, string | null>>> {
    return this.request("/api/v1/admin/settings/auth");
  }

  /** Update auth method config. */
  updateAuthSettings(data: AuthConfigUpdate): Promise<APIResponse<Record<string, string | null>>> {
    return this.request("/api/v1/admin/settings/auth", { method: "PUT", body: JSON.stringify(data) });
  }

  // ── Roles & Permissions ────────────────────────────────────────────────────

  listPermissions(): Promise<APIResponse<PermissionRead[]>> {
    return this.request("/api/v1/admin/permissions");
  }

  listRoles(): Promise<APIResponse<RoleRead[]>> {
    return this.request("/api/v1/admin/roles");
  }

  getRole(id: number): Promise<APIResponse<RoleRead>> {
    return this.request(`/api/v1/admin/roles/${id}`);
  }

  createRole(data: RoleCreate): Promise<APIResponse<RoleRead>> {
    return this.request("/api/v1/admin/roles", { method: "POST", body: JSON.stringify(data) });
  }

  updateRole(id: number, data: RoleUpdate): Promise<APIResponse<RoleRead>> {
    return this.request(`/api/v1/admin/roles/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }

  deleteRole(id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/admin/roles/${id}`, { method: "DELETE" });
  }

  setRolePermissions(id: number, data: RolePermissionsUpdate): Promise<APIResponse<RoleRead>> {
    return this.request(`/api/v1/admin/roles/${id}/permissions`, { method: "PUT", body: JSON.stringify(data) });
  }

  // ── Statistics ─────────────────────────────────────────────────────────────

  /** Get parishioner statistics summary. */
  getParishionerStats(): Promise<APIResponse<unknown>> {
    return this.request("/api/v1/statistics/parishioners");
  }

  // ── Users ──────────────────────────────────────────────────────────────────

  listUsers(
    params: PaginationParams = {}
  ): Promise<APIResponse<PagedData<User>>> {
    return this.request(
      `/api/v1/user-management${this.buildQuery(params)}`
    );
  }

  getUser(id: string): Promise<APIResponse<User>> {
    return this.request(`/api/v1/user-management/${id}`);
  }

  createUser(data: UserCreate): Promise<APIResponse<User>> {
    return this.request("/api/v1/user-management", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  updateUser(id: string, data: UserUpdate): Promise<APIResponse<User>> {
    return this.request(`/api/v1/user-management/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  deleteUser(id: string): Promise<APIResponse<null>> {
    return this.request(`/api/v1/user-management/${id}`, { method: "DELETE" });
  }

  // ── Leadership ────────────────────────────────────────────────────────────

  /** List leadership for the primary parish. currentOnly defaults to true. */
  listParishLeadership(currentOnly = true): Promise<APIResponse<LeadershipRead[]>> {
    return this.request(`/api/v1/parish/leadership${this.buildQuery({ current_only: currentOnly })}`);
  }

  createParishLeadership(data: LeadershipCreate): Promise<APIResponse<LeadershipRead>> {
    return this.request("/api/v1/parish/leadership", { method: "POST", body: JSON.stringify(data) });
  }

  updateParishLeadership(id: number, data: LeadershipUpdate): Promise<APIResponse<LeadershipRead>> {
    return this.request(`/api/v1/parish/leadership/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }

  deleteParishLeadership(id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/parish/leadership/${id}`, { method: "DELETE" });
  }

  listOutstationLeadership(outstationId: number, currentOnly = true): Promise<APIResponse<LeadershipRead[]>> {
    return this.request(`/api/v1/parish/outstations/${outstationId}/leadership${this.buildQuery({ current_only: currentOnly })}`);
  }

  createOutstationLeadership(outstationId: number, data: LeadershipCreate): Promise<APIResponse<LeadershipRead>> {
    return this.request(`/api/v1/parish/outstations/${outstationId}/leadership`, { method: "POST", body: JSON.stringify(data) });
  }

  updateOutstationLeadership(outstationId: number, id: number, data: LeadershipUpdate): Promise<APIResponse<LeadershipRead>> {
    return this.request(`/api/v1/parish/outstations/${outstationId}/leadership/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }

  deleteOutstationLeadership(outstationId: number, id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/parish/outstations/${outstationId}/leadership/${id}`, { method: "DELETE" });
  }

  listUnitLeadership(unitId: number, currentOnly = true): Promise<APIResponse<LeadershipRead[]>> {
    return this.request(`/api/v1/parish/units/${unitId}/leadership${this.buildQuery({ current_only: currentOnly })}`);
  }

  createUnitLeadership(unitId: number, data: LeadershipCreate): Promise<APIResponse<LeadershipRead>> {
    return this.request(`/api/v1/parish/units/${unitId}/leadership`, { method: "POST", body: JSON.stringify(data) });
  }

  getUnitLeadership(unitId: number, id: number): Promise<APIResponse<LeadershipRead>> {
    return this.request(`/api/v1/parish/units/${unitId}/leadership/${id}`);
  }

  updateUnitLeadership(unitId: number, id: number, data: LeadershipUpdate): Promise<APIResponse<LeadershipRead>> {
    return this.request(`/api/v1/parish/units/${unitId}/leadership/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }

  deleteUnitLeadership(unitId: number, id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/parish/units/${unitId}/leadership/${id}`, { method: "DELETE" });
  }

  // ── Church Events ─────────────────────────────────────────────────────────

  listParishEvents(params: { upcoming_only?: boolean; from_date?: string; to_date?: string } = {}): Promise<APIResponse<ChurchEventRead[]>> {
    return this.request(`/api/v1/parish/events${this.buildQuery(params)}`);
  }

  createParishEvent(data: ChurchEventCreate): Promise<APIResponse<ChurchEventRead>> {
    return this.request("/api/v1/parish/events", { method: "POST", body: JSON.stringify(data) });
  }

  updateParishEvent(id: number, data: ChurchEventUpdate): Promise<APIResponse<ChurchEventRead>> {
    return this.request(`/api/v1/parish/events/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }

  deleteParishEvent(id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/parish/events/${id}`, { method: "DELETE" });
  }

  listOutstationEvents(outstationId: number, params: { upcoming_only?: boolean; from_date?: string; to_date?: string } = {}): Promise<APIResponse<ChurchEventRead[]>> {
    return this.request(`/api/v1/parish/outstations/${outstationId}/events${this.buildQuery(params)}`);
  }

  createOutstationEvent(outstationId: number, data: ChurchEventCreate): Promise<APIResponse<ChurchEventRead>> {
    return this.request(`/api/v1/parish/outstations/${outstationId}/events`, { method: "POST", body: JSON.stringify(data) });
  }

  updateOutstationEvent(outstationId: number, id: number, data: ChurchEventUpdate): Promise<APIResponse<ChurchEventRead>> {
    return this.request(`/api/v1/parish/outstations/${outstationId}/events/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }

  deleteOutstationEvent(outstationId: number, id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/parish/outstations/${outstationId}/events/${id}`, { method: "DELETE" });
  }

  listUnitEvents(unitId: number, params: { upcoming_only?: boolean; from_date?: string; to_date?: string } = {}): Promise<APIResponse<ChurchEventRead[]>> {
    return this.request(`/api/v1/parish/units/${unitId}/events${this.buildQuery(params)}`);
  }

  createUnitEvent(unitId: number, data: ChurchEventCreate): Promise<APIResponse<ChurchEventRead>> {
    return this.request(`/api/v1/parish/units/${unitId}/events`, { method: "POST", body: JSON.stringify(data) });
  }

  getUnitEvent(unitId: number, id: number): Promise<APIResponse<ChurchEventRead>> {
    return this.request(`/api/v1/parish/units/${unitId}/events/${id}`);
  }

  updateUnitEvent(unitId: number, id: number, data: ChurchEventUpdate): Promise<APIResponse<ChurchEventRead>> {
    return this.request(`/api/v1/parish/units/${unitId}/events/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }

  deleteUnitEvent(unitId: number, id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/parish/units/${unitId}/events/${id}`, { method: "DELETE" });
  }

  // ── Messaging ──────────────────────────────────────────────────────────────

  getMessageTemplates(): Promise<APIResponse<{ message_templates: { id: string; name: string; content: string | null }[]; available_variables: { name: string; description: string }[] }>> {
    return this.request("/api/v1/messaging/templates");
  }

  sendBulkMessage(data: {
    parishioner_ids: string[];
    channel: "email" | "sms" | "both";
    template: string;
    custom_message?: string;
    subject?: string;
    event_name?: string;
    event_date?: string;
    event_time?: string;
  }): Promise<APIResponse<{ queued_count: number }>> {
    return this.request("/api/v1/messaging/send", { method: "POST", body: JSON.stringify(data) });
  }

  scheduleMessage(data: {
    parishioner_ids: string[];
    channel: "email" | "sms" | "both";
    template: string;
    custom_message?: string;
    subject?: string;
    event_name?: string;
    event_date?: string;
    event_time?: string;
    send_at: string;
  }): Promise<APIResponse<{ id: number; send_at: string; recipient_count: number; channel: string; template: string }>> {
    return this.request("/api/v1/messaging/schedule", { method: "POST", body: JSON.stringify(data) });
  }

  listScheduledMessages(params: { status_filter?: string; skip?: number; limit?: number } = {}): Promise<APIResponse<PagedData<ScheduledMessageRead>>> {
    return this.request(`/api/v1/messaging/scheduled${this.buildQuery(params)}`);
  }

  cancelScheduledMessage(id: number): Promise<APIResponse<null>> {
    return this.request(`/api/v1/messaging/scheduled/${id}`, { method: "DELETE" });
  }
}
