// AUTO-GENERATED — do not edit by hand.
// Regenerate with: make sdk
//
// Generated from FastAPI OpenAPI schema via scripts/gen_sdk.py

// ── Response wrappers ──────────────────────────────────────────────────────

export interface APIResponse<T = unknown> {
  message: string;
  data: T | null;
}

/** Standard paginated payload — always lives inside APIResponse.data */
export interface PagedData<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export type PagedResponse<T> = APIResponse<PagedData<T>>;


// ── Generated schema types ───────────────────────────────────────────────────

export interface APIResponse {
  message: string;
  data: unknown | null;
}

export interface AddMembersRequest {
  members: MemberData[];
}

export interface AppConfigUpdate {
  name?: string | null;
  description?: string | null;
  version?: string | null;
  church_code?: string | null;
  currency_symbol?: string | null;
  currency_code?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  website?: string | null;
  address?: string | null;
  logo_url?: string | null;
  support_email?: string | null;
}

export interface AuthConfigUpdate {
  password_enabled?: boolean | null;
  otp_sms_enabled?: boolean | null;
  otp_email_enabled?: boolean | null;
  otp_expiry_minutes?: number | null;
  otp_code_length?: number | null;
}

export interface BodyAuthenticationLogin {
  grant_type?: string | null;
  username: string;
  password: string;
  scope?: string;
  client_id?: string | null;
  client_secret?: string | null;
}

export interface BodyParishionerUploadParishionersCsv {
  file: string;
}

export interface BulkMessageIn {
  parishioner_ids: string[];
  channel?: "email" | "sms" | "both";
  custom_message?: string | null;
  template?: string;
  subject?: string | null;
  event_name?: string | null;
  event_date?: string | null;
  event_time?: string | null;
}

export interface ChildUpdate {
  name: string;
}

export interface ChurchCommunityCreate {
  name: string;
  description?: string | null;
  location?: string | null;
  is_active?: boolean;
}

export interface ChurchCommunityUpdate {
  name?: string | null;
  description?: string | null;
  location?: string | null;
  is_active?: boolean | null;
}

export interface ChurchEventCreate {
  name: string;
  description?: string | null;
  event_date: string;
  start_time?: string | null;
  end_time?: string | null;
  location?: string | null;
  is_public?: boolean;
}

export interface ChurchEventUpdate {
  name?: string | null;
  description?: string | null;
  event_date?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  location?: string | null;
  is_public?: boolean | null;
}

export interface ChurchUnitCreate {
  type: ChurchUnitType;
  parent_id?: number | null;
  name: string;
  diocese?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  established_date?: string | null;
  pastor_name?: string | null;
  pastor_email?: string | null;
  pastor_phone?: string | null;
  location_description?: string | null;
  google_maps_url?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  priest_in_charge?: string | null;
  priest_phone?: string | null;
}

export type ChurchUnitType = "parish" | "outstation";

export interface ChurchUnitUpdate {
  name?: string | null;
  parent_id?: number | null;
  diocese?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  established_date?: string | null;
  pastor_name?: string | null;
  pastor_email?: string | null;
  pastor_phone?: string | null;
  location_description?: string | null;
  google_maps_url?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  priest_in_charge?: string | null;
  priest_phone?: string | null;
  is_active?: boolean | null;
}

export type DayOfWeek = "sunday" | "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday";

export interface EmergencyContactCreate {
  name: string;
  relationship: string;
  primary_phone: string;
  alternative_phone?: string | null;
}

export interface EmergencyContactUpdate {
  name?: string | null;
  relationship?: string | null;
  primary_phone?: string | null;
  alternative_phone?: string | null;
}

export interface FamilyInfoUpdate {
  spouse_name?: string | null;
  spouse_status?: string | null;
  spouse_phone?: string | null;
  father_name?: string | null;
  father_status?: LifeStatus | null;
  mother_name?: string | null;
  mother_status?: LifeStatus | null;
  children?: ChildUpdate[] | null;
}

export type Gender = "male" | "female" | "other";

export interface LanguageCreate {
  name: string;
  description: string | null;
}

export interface LanguageUpdate {
  name: string;
  description: string | null;
}

export interface LanguagesAssignRequest {
  language_ids: number[];
}

export interface LeadershipCreate {
  role: AppModelsChurchUnitAdminLeadershiprole;
  custom_role?: string | null;
  name: string;
  phone?: string | null;
  email?: string | null;
  is_current?: boolean;
  start_date?: string | null;
  end_date?: string | null;
  notes?: string | null;
}

export interface LeadershipUpdate {
  role?: AppModelsChurchUnitAdminLeadershiprole | null;
  custom_role?: string | null;
  name?: string | null;
  phone?: string | null;
  email?: string | null;
  is_current?: boolean | null;
  start_date?: string | null;
  end_date?: string | null;
  notes?: string | null;
}

export type LifeStatus = "alive" | "deceased" | "unknown";

export type LoginMethod = "password" | "email_otp" | "sms_otp";

export interface LoginResponse {
  access_token: string;
  token_type?: string;
  user: User;
}

export type MaritalStatus = "single" | "married" | "widowed" | "divorced" | "separated";

export interface MassScheduleCreate {
  day_of_week: DayOfWeek;
  time: string;
  mass_type?: MassType;
  language?: string;
  description?: string | null;
}

export interface MassScheduleUpdate {
  day_of_week?: DayOfWeek | null;
  time?: null;
  mass_type?: MassType;
  language?: string;
  description?: string | null;
  is_active?: boolean | null;
}

export type MassType = "sunday" | "weekday" | "saturday" | "holy_day" | "special";

export interface MedicalConditionCreate {
  condition: string;
  notes?: string | null;
}

export interface MedicalConditionUpdate {
  condition?: string | null;
  notes?: string | null;
}

export type MeetingFrequency = "weekly" | "biweekly" | "monthly" | "quarterly" | "custom";

export interface MemberData {
  parishioner_id: string;
  date_joined?: string;
}

export type MembershipStatus = "active" | "deceased" | "disabled";

export interface OTPRequestBody {
  identifier: string;
}

export interface OTPVerifyBody {
  identifier: string;
  code: string;
}

export interface OccupationCreate {
  role: string;
  employer: string;
}

export interface OccupationUpdate {
  role?: string | null;
  employer?: string | null;
}

export interface OutstationCreate {
  type?: ChurchUnitType;
  parent_id?: number | null;
  name: string;
  diocese?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  established_date?: string | null;
  pastor_name?: string | null;
  pastor_email?: string | null;
  pastor_phone?: string | null;
  location_description?: string | null;
  google_maps_url?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  priest_in_charge?: string | null;
  priest_phone?: string | null;
}

export interface ParSacramentCreate {
  date_received?: string | null;
  place?: string | null;
  minister?: string | null;
  notes?: string | null;
  sacrament_id: number | SacramentType;
}

export interface ParishionerCreate {
  title?: string | null;
  old_church_id?: string | null;
  new_church_id?: string | null;
  first_name: string;
  other_names?: string | null;
  last_name: string;
  maiden_name?: string | null;
  baptismal_name?: string | null;
  gender: Gender;
  date_of_birth?: string | null;
  place_of_birth?: string | null;
  nationality?: string | null;
  hometown?: string | null;
  region?: string | null;
  country?: string | null;
  marital_status?: MaritalStatus | null;
  mobile_number?: string | null;
  whatsapp_number?: string | null;
  email_address?: string | null;
  current_residence?: string | null;
  is_deceased?: boolean | null;
  date_of_death?: string | null;
  photo_url?: string | null;
  notes?: string | null;
  membership_status?: MembershipStatus | null;
  verification_status?: VerificationStatus | null;
}

export interface ParishionerPartialUpdate {
  title?: string | null;
  old_church_id?: string | null;
  new_church_id?: string | null;
  first_name?: string | null;
  other_names?: string | null;
  last_name?: string | null;
  maiden_name?: string | null;
  baptismal_name?: string | null;
  gender?: Gender | null;
  date_of_birth?: string | null;
  place_of_birth?: string | null;
  nationality?: string | null;
  hometown?: string | null;
  region?: string | null;
  country?: string | null;
  marital_status?: MaritalStatus | null;
  mobile_number?: string | null;
  whatsapp_number?: string | null;
  email_address?: string | null;
  church_unit_id?: number | null;
  church_community_id?: string | null;
  current_residence?: string | null;
  is_deceased?: boolean | null;
  date_of_death?: string | null;
  photo_url?: string | null;
  notes?: string | null;
  membership_status?: MembershipStatus | null;
  verification_status?: VerificationStatus | null;
}

export interface PasswordResetRequest {
  email: string;
  temp_password: string;
  new_password: string;
}

export interface PasswordResetResponse {
  message: string;
  access_token: string;
  token_type?: string;
  user: User;
}

export interface RemoveMembersRequest {
  parishioner_ids: string[];
}

export interface RoleCreate {
  name: string;
  label: string;
  description?: string | null;
}

export interface RolePermissionsUpdate {
  permission_ids: number[];
}

export interface RoleUpdate {
  label?: string | null;
  description?: string | null;
}

export type SacramentType = "Baptism" | "First Communion" | "Confirmation" | "Penance" | "Anointing of the Sick" | "Holy Orders" | "Holy Matrimony";

export interface SacramentUpdate {
  type?: SacramentType | null;
  date?: string | null;
  place?: string | null;
  minister?: string | null;
}

export interface ScheduleMessageIn {
  parishioner_ids: string[];
  channel?: string;
  template?: string;
  custom_message?: string | null;
  subject?: string | null;
  event_name?: string | null;
  event_date?: string | null;
  event_time?: string | null;
  send_at: string;
}

export interface SettingsBulkUpdate {
  settings: Record<string, unknown>;
}

export interface SkillBase {
  name: string;
}

export interface SkillCreate {
  name: string;
}

export interface SocietyCreate {
  name: string;
  description?: string | null;
  date_inaugurated?: string | null;
  is_active?: boolean;
  church_unit_id?: number | null;
  meeting_frequency: MeetingFrequency;
  meeting_day?: string | null;
  meeting_time?: string | null;
  meeting_venue?: string | null;
}

export interface SocietyLeadershipCreate {
  role: AppModelsSocietyLeadershiprole;
  custom_role?: string | null;
  elected_date?: string | null;
  end_date?: string | null;
  parishioner_id: string;
}

export interface SocietyLeadershipUpdate {
  role?: AppModelsSocietyLeadershiprole | null;
  custom_role?: string | null;
  elected_date?: string | null;
  end_date?: string | null;
  parishioner_id?: number | null;
}

export interface SocietyUpdate {
  name?: string | null;
  description?: string | null;
  date_inaugurated?: string | null;
  is_active?: boolean | null;
  church_unit_id?: number | null;
  meeting_frequency?: MeetingFrequency | null;
  meeting_day?: string | null;
  meeting_time?: string | null;
  meeting_venue?: string | null;
}

export interface UpdateMemberStatusRequest {
  status: MembershipStatus;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  login_method?: LoginMethod;
  role?: string | null;
  role_label?: string | null;
  church_unit_id?: number | null;
  church_unit_name?: string | null;
  status: UserStatus;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  email: string;
  full_name: string;
  status?: UserStatus | null;
  password?: string | null;
  phone?: string | null;
  login_method?: LoginMethod | null;
  role_name?: string | null;
  church_unit_id?: number | null;
}

export type UserStatus = "active" | "disabled" | "reset_required";

export interface UserUpdate {
  full_name?: string | null;
  phone?: string | null;
  login_method?: LoginMethod | null;
  role_name?: string | null;
  status?: UserStatus | null;
  church_unit_id?: number | null;
}

export type VerificationStatus = "unverified" | "verified" | "pending";

export type AppModelsChurchUnitAdminLeadershiprole = "priest_in_charge" | "assistant_priest" | "deacon" | "church_administrator" | "church_secretary" | "ppc_chairman" | "ppc_vice_chairman" | "ppc_secretary" | "ppc_treasurer" | "ppc_member" | "other";

export type AppModelsSocietyLeadershiprole = "President" | "Vice President" | "Secretary" | "Treasurer" | "Chaplain" | "Coordinator" | "Patron" | "Other";


// ── Aliases ──────────────────────────────────────────────────────────────────

export type LeadershipRole = AppModelsChurchUnitAdminLeadershiprole;

export type SocietyLeadershipRole = AppModelsSocietyLeadershiprole;


// ── Pagination helpers ────────────────────────────────────────────────────────

export interface PaginationParams {
  skip?: number;
  limit?: number;
}


// ── Response / read types ─────────────────────────────────────────────────────

export interface MassSchedule {
  id: number;
  church_unit_id: number;
  day_of_week: DayOfWeek;
  time: string;
  mass_type: MassType;
  language: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChurchUnit {
  id: number;
  type: ChurchUnitType;
  parent_id?: number | null;
  name: string;
  diocese?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  established_date?: string | null;
  pastor_name?: string | null;
  pastor_email?: string | null;
  pastor_phone?: string | null;
  location_description?: string | null;
  google_maps_url?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  priest_in_charge?: string | null;
  priest_phone?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SocietySummary {
  id: number;
  name: string;
  description?: string | null;
  meeting_day?: string | null;
  meeting_time?: string | null;
  meeting_venue?: string | null;
}

export interface CommunitySummary {
  id: number;
  name: string;
  description?: string | null;
  location?: string | null;
}

export interface OutstationDetail extends ChurchUnit {
  mass_schedules: MassSchedule[];
  societies: SocietySummary[];
  communities: CommunitySummary[];
}

export interface ParishDetail extends ChurchUnit {
  mass_schedules: MassSchedule[];
  societies: SocietySummary[];
  communities: CommunitySummary[];
  outstations: OutstationDetail[];
}

export interface LeadershipRead {
  id: number;
  church_unit_id: number;
  role: LeadershipRole;
  custom_role?: string | null;
  name: string;
  phone?: string | null;
  email?: string | null;
  is_current: boolean;
  start_date?: string | null;
  end_date?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChurchEventRead {
  id: number;
  church_unit_id: number;
  name: string;
  description?: string | null;
  event_date: string;
  start_time?: string | null;
  end_time?: string | null;
  location?: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface SocietyLeadershipRead {
  id: number;
  role: SocietyLeadershipRole;
  custom_role?: string | null;
  elected_date?: string | null;
  end_date?: string | null;
  parishioner_id: string;
  parishioner_name: string;
  parishioner_church_id?: string | null;
  parishioner_contact?: string | null;
}

export interface Society {
  id: number;
  name: string;
  description?: string | null;
  date_inaugurated?: string | null;
  is_active: boolean;
  church_unit_id?: number | null;
  church_unit_name?: string | null;
  meeting_frequency: MeetingFrequency;
  meeting_day?: string | null;
  meeting_time?: string | null;
  meeting_venue?: string | null;
  members_count: number;
  leadership: SocietyLeadershipRead[];
  created_at: string;
  updated_at: string;
}

export interface SocietyMember {
  parishioner_id: string;
  first_name: string;
  last_name: string;
  other_names?: string | null;
  mobile_number?: string | null;
  date_joined?: string | null;
  membership_status?: string | null;
}

export interface ChurchCommunity {
  id: number;
  name: string;
  description?: string | null;
  location?: string | null;
  is_active: boolean;
  church_unit_id: number;
  created_at: string;
  updated_at: string;
}

export interface Parishioner {
  id: string;
  title?: string | null;
  old_church_id?: string | null;
  new_church_id?: string | null;
  first_name: string;
  other_names?: string | null;
  last_name: string;
  maiden_name?: string | null;
  baptismal_name?: string | null;
  gender: Gender;
  date_of_birth?: string | null;
  place_of_birth?: string | null;
  nationality?: string | null;
  hometown?: string | null;
  region?: string | null;
  country?: string | null;
  marital_status?: MaritalStatus | null;
  mobile_number?: string | null;
  whatsapp_number?: string | null;
  email_address?: string | null;
  current_residence?: string | null;
  is_deceased: boolean;
  date_of_death?: string | null;
  photo_url?: string | null;
  notes?: string | null;
  church_community_id?: number | null;
  church_unit_id?: number | null;
  membership_status?: MembershipStatus | null;
  verification_status?: VerificationStatus | null;
  created_at: string;
  updated_at: string;
}

export interface ScheduledMessageRead {
  id: number;
  channel: string;
  template: string;
  custom_message?: string | null;
  subject?: string | null;
  event_name?: string | null;
  event_date?: string | null;
  event_time?: string | null;
  send_at: string;
  status: "pending" | "processing" | "sent" | "failed" | "cancelled";
  sent_count: number;
  error_message?: string | null;
  recipient_count: number;
  created_at: string;
}

export interface ParishionerDetailed extends Parishioner {
  occupation?: { id: number; role: string; employer: string } | null;
  family?: {
    spouse_name?: string | null;
    spouse_status?: string | null;
    spouse_phone?: string | null;
    father_name?: string | null;
    father_status?: string | null;
    mother_name?: string | null;
    mother_status?: string | null;
    children?: Array<{ name: string }>;
  } | null;
  emergency_contacts: Array<{
    id: number;
    name: string;
    relationship: string;
    primary_phone: string;
    alternative_phone?: string | null;
  }>;
  medical_conditions: Array<{ id: number; condition: string; notes?: string | null }>;
  skills: Array<{ id: number; name: string }>;
  sacraments: Array<{
    id: number;
    sacrament: { id: number; type: string };
    date_received?: string | null;
    place?: string | null;
    minister?: string | null;
    notes?: string | null;
  }>;
  societies: Array<{ id: number; name: string; date_joined?: string | null }>;
}

export interface ParishionerFilters extends PaginationParams {
  search?: string;
  gender?: Gender;
  marital_status?: MaritalStatus;
  membership_status?: MembershipStatus;
  verification_status?: VerificationStatus;
  church_unit_id?: number;
  church_community_id?: number;
}

/** Alias — ParishionerUpdate and ParishionerPartialUpdate are the same shape. */
export type ParishionerUpdate = ParishionerPartialUpdate;

export interface PermissionRead {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  module: string;
}

export interface RoleRead {
  id: number;
  name: string;
  label: string;
  description?: string | null;
  is_system: boolean;
  permissions: PermissionRead[];
  created_at: string;
  updated_at: string;
}

export interface SettingRead {
  id: number;
  key: string;
  value?: string | null;
  label?: string | null;
  description?: string | null;
  church_unit_id: number;
  created_at: string;
  updated_at: string;
}
