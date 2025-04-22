import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import {apiService} from "@/lib/api-config";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export async function gotoAuthPage() {
  const res = await apiService.fetchData('/tmdb/request-token');
  const { request_token } = await res.json()
  const redirectUrl = `${window.location.origin}/tmdb-auth`
  window.location.href = `https://www.themoviedb.org/authenticate/${request_token}?redirect_to=${redirectUrl}`
}