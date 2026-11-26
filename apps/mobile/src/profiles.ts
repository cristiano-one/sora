export type BusinessProfile =
  | "MEDICAL_CLINIC"
  | "AESTHETICS"
  | "PODOLOGY"
  | "SALON"
  | "BARBERSHOP"
  | "GENERAL";

const MEDICAL_PROFILES: BusinessProfile[] = [
  "MEDICAL_CLINIC",
  "AESTHETICS",
  "PODOLOGY",
];

export function supportsMedicalRecords(
  profile: BusinessProfile | undefined,
): boolean {
  return profile ? MEDICAL_PROFILES.includes(profile) : false;
}
