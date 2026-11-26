export type BusinessProfile =
  | "MEDICAL_CLINIC"
  | "AESTHETICS"
  | "PODOLOGY"
  | "SALON"
  | "BARBERSHOP"
  | "GENERAL";

export type BusinessProfileOption = {
  value: BusinessProfile;
  label: string;
  description: string;
  medicalRecords: boolean;
};

export const BUSINESS_PROFILES: BusinessProfileOption[] = [
  {
    value: "MEDICAL_CLINIC",
    label: "Clínica médica",
    description:
      "Prontuário, anamnese, evoluções clínicas, LGPD e agenda multi-profissional.",
    medicalRecords: true,
  },
  {
    value: "AESTHETICS",
    label: "Clínica de estética",
    description:
      "Prontuário de anamnese, fotos antes/depois, pacotes e clube de assinatura.",
    medicalRecords: true,
  },
  {
    value: "PODOLOGY",
    label: "Podologia",
    description:
      "Ficha clínica, evolução do tratamento, fotos e recorrência de sessões.",
    medicalRecords: true,
  },
  {
    value: "SALON",
    label: "Salão de beleza",
    description:
      "Agenda, clientes, pacotes, assinaturas, estoque, comissões e financeiro.",
    medicalRecords: false,
  },
  {
    value: "BARBERSHOP",
    label: "Barbearia",
    description:
      "Agenda, clientes, pacotes, assinaturas, estoque, comissões e financeiro.",
    medicalRecords: false,
  },
  {
    value: "GENERAL",
    label: "Multisserviços",
    description:
      "Operação comercial completa sem prontuário clínico. Perfil inicial de novas empresas.",
    medicalRecords: false,
  },
];

export function profileOption(
  profile: BusinessProfile,
): BusinessProfileOption {
  return (
    BUSINESS_PROFILES.find((item) => item.value === profile) ??
    BUSINESS_PROFILES[BUSINESS_PROFILES.length - 1]
  );
}

export function supportsMedicalRecords(profile: BusinessProfile): boolean {
  return profileOption(profile).medicalRecords;
}
