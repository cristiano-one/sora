import * as SecureStore from "expo-secure-store";

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

const ACCESS_KEY = "sora_access_token";
const REFRESH_KEY = "sora_refresh_token";

let accessToken: string | null = null;
let refreshToken: string | null = null;

export async function hydrateTokens(): Promise<void> {
  accessToken = await SecureStore.getItemAsync(ACCESS_KEY);
  refreshToken = await SecureStore.getItemAsync(REFRESH_KEY);
}

export async function saveTokens(pair: TokenPair): Promise<void> {
  accessToken = pair.access_token;
  refreshToken = pair.refresh_token;
  await SecureStore.setItemAsync(ACCESS_KEY, pair.access_token);
  await SecureStore.setItemAsync(REFRESH_KEY, pair.refresh_token);
}

export async function getAccessToken(): Promise<string | null> {
  if (accessToken) return accessToken;
  accessToken = await SecureStore.getItemAsync(ACCESS_KEY);
  return accessToken;
}

export async function getRefreshToken(): Promise<string | null> {
  if (refreshToken) return refreshToken;
  refreshToken = await SecureStore.getItemAsync(REFRESH_KEY);
  return refreshToken;
}

export async function clearTokens(): Promise<void> {
  accessToken = null;
  refreshToken = null;
  await SecureStore.deleteItemAsync(ACCESS_KEY);
  await SecureStore.deleteItemAsync(REFRESH_KEY);
}
